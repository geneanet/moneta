# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging
from datetime import datetime
import pytz
from pwd import getpwnam
from grp import getgrnam
from os import setgid, setuid, setgroups, chdir, environ
import json
import uuid
from locale import getpreferredencoding

from gevent.subprocess import Popen
from subprocess import PIPE
from gevent import Greenlet, GreenletExit

from moneta.http.client import HTTPClient
from moneta.http.http import HTTPRequest, parse_host_port
from moneta.exceptions import ExecutionDisabled

logger = logging.getLogger('moneta.manager')

class MonetaManager(object):
    """ Execute tasks, keeping log of what is running """

    def __init__(self, cluster):
        self.cluster = cluster
        self.running_processes = {}
        self.enabled = True

    def shutdown(self, kill = False):
        """Disable new executions and either wait for all currently running tasks to finish or kill them"""

        logger.info("Shutting down manager: disabling task execution on this node")

        self.enabled = False

        if kill:
            self.kill_all()
        else:
            self.wait_until_finished()

    def wait_until_finished(self):
        """Wait for all currently running tasks to finish"""

        greenlets = [ process['greenlet'] for process in self.running_processes.itervalues() ]

        logger.debug("Waiting for %d currently running tasks to finish", len(greenlets))

        for greenlet in greenlets:
            greenlet.join()

    def kill_all(self, wait = True):
        """Kill all running tasks"""

        greenlets = [ process['greenlet'] for process in self.running_processes.itervalues() ]

        logger.debug("Killing %d currently running tasks", len(greenlets))

        for greenlet in greenlets:
            greenlet.kill(block = wait)

    def execute_task(self, task):
        """Spawn a greenlet to execute a task"""

        if not self.enabled:
            raise ExecutionDisabled()

        execid = uuid.uuid1().hex

        greenlet = Greenlet(self._execute_task, task)

        def handle_task_completion(greenlet, execid = execid):
            del self.running_processes[execid]

        greenlet.link(handle_task_completion)

        self.running_processes[execid] = {
            "task": task,
            "started": datetime.utcnow().replace(tzinfo = pytz.utc),
            "greenlet": greenlet
        }

        greenlet.start()

    def _execute_task(self, task):
        """Execute a task and send the results to the master"""

        logger.info("Running task %s", task)

        start = datetime.utcnow().replace(tzinfo = pytz.utc)

        report = {
            "node": self.cluster.nodename,
            "task": task,
            "start_time": start.isoformat()
        }

        try:
            taskconfig = self.cluster.config['tasks'][task]

            def drop_privileges():
                """Change user, group and workdir before running the process"""
                if 'group' in taskconfig and taskconfig['group']:
                    group = getgrnam(taskconfig['group']).gr_gid
                    setgroups([])
                    setgid(group)

                if 'user' in taskconfig and taskconfig['user']:
                    user = getpwnam(taskconfig['user']).pw_uid
                    setuid(user)

                if 'workdir' in taskconfig and taskconfig['workdir']:
                    workdir = taskconfig['workdir']
                    chdir(workdir)

            args = taskconfig['command']

            if 'env' in taskconfig:
                env = dict(environ)
                env.update(taskconfig['env'])
            else:
                env = dict(environ)

            process = Popen(args = args, shell = True, preexec_fn = drop_privileges, stdout = PIPE, stderr = PIPE, env = env)

            (stdout, stderr) = process.communicate()
            returncode = process.returncode

            if returncode == 0:
                status = "ok"
            else:
                status = "error"

            def decodestring(string, encoding = None):
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

            report.update({
                "status": status,
                "returncode": returncode,
                "stdout": decodestring(stdout),
                "stderr": decodestring(stderr)
            })

        except GreenletExit:
            logger.info("Killing currently running task %s", task)
            if process:
                process.kill()

            report.update({
                "status": "fail",
                "error": "Killed"
            })

        except Exception, e:
            logger.exception("Encountered an exception while running task %s", task)

            report.update({
                "status": "fail",
                "error": str(e)
            })

        finally:
            try:
                end = datetime.utcnow().replace(tzinfo = pytz.utc)

                report.update({
                    "end_time": end.isoformat(),
                    "duration": (end - start).total_seconds()
                })

                logger.info("Reporting task %s execution results to master", task)

                addr = parse_host_port(self.cluster.nodes[self.cluster.master]['address'])
                client = HTTPClient(addr)
                ret = client.request(HTTPRequest(uri = '/tasks/%s/report' % task, method = 'POST', body = json.dumps(report)))

                if ret.code != 200:
                    logger.error("Encountered an error while sending task %s execution report. Master returned %d.", task, ret.code)

            except Exception, e:
                logger.exception("Encountered an exception while running task %s", task)
