# -*- coding: utf-8 -*-



import logging
import gevent
from gevent import Greenlet, GreenletExit, sleep
from gevent.subprocess import Popen, PIPE
from gevent.hub import signal as signal_handler
from datetime import datetime, timedelta
import dateutil.tz
from os import setgid, setuid, setgroups, chdir, environ, getpid, setsid, killpg, getpgid
from pwd import getpwnam
from grp import getgrnam
from locale import getpreferredencoding
import sys
import signal
from collections import deque

from moneta import json
from moneta.http.client import HTTPClient
from moneta.http.http import HTTPRequest, parse_host_port

logger = logging.getLogger('moneta.watcher')

class MonetaWatcher(object):
    """ Watch a process and send updates back to the manager. """

    def __init__(self, nodename):
        """ Constructor """

        self.task = None
        self.taskconfig = {}
        self.processid = None
        self.manager = None
        self.nodename = nodename

        self.report = {}
        self.exec_greenlet = None
        self.notify_greenlet = None
        self.last_notification = datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc())
        self.disable_notify = False

        self.notify_delay = 1
        self.giveup_notify_after = 10

        self.output_buffer_lines = 1000
        self.output_buffer_line_size = 10000

    @staticmethod
    def spawn(processid, task, taskconfig, manager):
        """ Spawn a new watcher in another process """

        path = list(sys.argv)
        path.append('--watcher')

        process = Popen(args = path, stdin = PIPE, preexec_fn = setsid)
        process.stdin.write(json.dumps({
            "manager": manager,
            "task": task,
            "processid": processid,
            "taskconfig": taskconfig
        }).encode())
        process.stdin.close()
        logger.debug('Process %s (task %s) spawned and configured.', processid, task)

    def run(self):
        """ Run in Watcher Mode """

        # Signals
        def handle_clean_exit():
            """ On SIGTERM, propagate to the running process """
            logger.info('Termination signal received.')
            # Kill the runnning process
            if self.exec_greenlet:
                self.exec_greenlet.kill()
        signal_handler(signal.SIGTERM, handle_clean_exit)

        # Config
        logger.debug('Reading configuration')
        data = json.loads(sys.stdin.read())
        self.processid = data['processid']
        self.task = data['task']
        self.taskconfig = data['taskconfig']
        self.manager = data['manager']

        # Initial report
        start = datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc())
        self.report.update({
            "node": self.nodename,
            "task": self.task,
            "pid": getpid(),
            "start_time": start,
            "status": "running",
            "finished": False
        })

        try:
            logger.debug('Executing task')

            # Start the task
            self.exec_greenlet = Greenlet(self._execute_task)
            def handle_task_completion(_):
                # When the task is complete, notify the manager and exit
                logger.debug('Task has finished running.')
                now = datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc())
                self.report.update({
                    "end_time": now,
                    "duration": (now - self.report['start_time']).total_seconds(),
                    "finished": True
                })
                self._notify_manager()
            self.exec_greenlet.link(handle_task_completion)
            self.exec_greenlet.start()

            # Start the notify loop
            def notify_loop():
                while True:
                    # Notify the manager regularly
                    self._notify_manager()
                    sleep(self.notify_delay)
            self.notify_greenlet = Greenlet(notify_loop)
            self.notify_greenlet.start()

            # Wait forever
            while True:
                sleep(1)

        # If we catch an exception, still try notify the manager
        except Exception as e:
            # Update the report and send it
            now = datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc())
            self.report.update({
                "end_time": now,
                "duration": (now - self.report['start_time']).total_seconds(),
                "finished": True,
                "status": "fail",
                "error": str(e)
            })
            self._notify_manager()
            exit(1)

    def _notify_manager(self):
        """ Notify the manager about the status of the process """

        # Ensure this function can only be run once at a time
        if self.disable_notify:
            return
        self.disable_notify = True

        try:
            report = self.report.copy()
            # Send the report
            client = HTTPClient(parse_host_port(self.manager))
            client.request(HTTPRequest(uri = '/processes/%s' % self.processid, method = 'UPDATE', body = json.dumps(report)))
            # If the task is finished and the report was sent, exit
            if report['finished']:
                exit(0)
            # Update the last notification timestamp
            self.last_notification = datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc())

        except Exception as e:
            logger.warning('Unable to notify the manager about process %s (%s)', self.processid, repr(e))
            giveup_after = self.last_notification + timedelta(seconds = self.giveup_notify_after)
            now = datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc())
            # If the manager is unreachable for more than self.giveup_notify_after seconds and the task is finished, give up
            if self.report['finished'] and now > giveup_after:
                logger.error('Giving up after %d seconds.', self.giveup_notify_after)
                exit(1)
        
        # Allow the function to be run again
        finally:
            self.disable_notify = False

  
    def _execute_task(self):
        """ Execute the task, updating the report as the situation changes """
                
        try:
            def drop_privileges():
                """Change user, group and workdir before running the process"""

                # Create a process group
                setsid()

                # Change group
                if 'group' in self.taskconfig and self.taskconfig['group']:
                    group = getgrnam(self.taskconfig['group']).gr_gid
                    setgroups([])
                    setgid(group)

                # Change user
                if 'user' in self.taskconfig and self.taskconfig['user']:
                    user = getpwnam(self.taskconfig['user']).pw_uid
                    setuid(user)

                # Change working directory
                if 'workdir' in self.taskconfig and self.taskconfig['workdir']:
                    workdir = self.taskconfig['workdir']
                    chdir(workdir)

            args = self.taskconfig['command']

            # Prepare environment variables
            if 'env' in self.taskconfig:
                env = dict(environ)
                env.update(self.taskconfig['env'])
            else:
                env = dict(environ)

            # Run process
            process = Popen(args = args, shell = True, preexec_fn = drop_privileges, stdout = PIPE, stderr = PIPE, env = env)

            output = {
                'buffer': deque(maxlen=self.output_buffer_lines),
                'bytes': {
                    'stdout': 0,
                    'stderr': 0
                }
            }

            def read_output(handle, channel, output):
                try:
                    while True:
                        data = handle.readline(self.output_buffer_line_size)
                        if data:
                            now = datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc())
                            decoded_data = self.decodestring(data).rstrip()
                            output['bytes'][channel] += len(data)
                            output['buffer'].append({'time': now, 'channel': channel, 'text': decoded_data})
                            logger.debug('Got "%s" on %s', decoded_data, channel)
                        else:
                            logger.debug('Got EOF on %s', channel)
                            return
                        gevent.idle()
                except RuntimeError as e:
                    logger.debug('Got error %s while reading %s', e, channel)
                    return            

            stdout_greenlet = gevent.spawn(read_output, process.stdout, 'stdout', output)
            stderr_greenlet = gevent.spawn(read_output, process.stderr, 'stderr', output)

            gevent.joinall([stdout_greenlet, stderr_greenlet])
            process.wait()

            process.stdout.close()
            process.stderr.close()

            output['buffer'] = list(output['buffer'])
            returncode = process.returncode

            if returncode == 0:
                status = "ok"
            else:
                status = "error"

            self.report.update({
                "status": status,
                "returncode": returncode,
                "output": output
            })

        except GreenletExit:
            logger.info("Killing currently running task %s", self.task)

            # Send SIGTERM to the processgroup
            if process:
                pgrp = getpgid(process.pid)
                killpg(pgrp, signal.SIGTERM)

            self.report.update({
                "status": "fail",
                "error": "killed"
            })

        except Exception as e:
            logger.exception("Encountered an exception while running task %s", self.task)

            self.report.update({
                "status": "fail",
                "error": str(e)
            })

    def decodestring(self, string, encoding = None):
        """ Decode a string to utf-8. If encoding is not specified, try several ones, and finally fallback on ascii. """
        try:
            if encoding:
                return string.decode(encoding, 'replace')

            else:
                encodings = [ getpreferredencoding(), 'utf-8', 'iso-8859-1' ]

                for encoding in encodings:
                    try:
                        return string.decode(encoding)

                    except UnicodeDecodeError:
                        continue

        except UnicodeError:
            return string.decode('ascii', 'replace')
        
        return string.decode('ascii', 'replace')
