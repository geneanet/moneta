# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging
from datetime import datetime, timedelta
import dateutil.tz
import uuid
import re
import os, signal

from gevent import Greenlet, sleep

from moneta import json
from moneta.http.server import HTTPServer
from moneta.http.http import HTTPReply, parse_host_port
from moneta.exceptions import ExecutionDisabled, ProcessNotFound
from moneta.watcher import MonetaWatcher

logger = logging.getLogger('moneta.manager')

class MonetaManager(HTTPServer):
    """ Execute tasks, keeping log of what is running """

    allowed_methods = [
        'UPDATE'
    ]

    def __init__(self, cluster, address = '127.0.0.1:32001'):
        """ Constructor """
        HTTPServer.__init__(self, parse_host_port(address), request_log_level = logging.DEBUG)
        self.register_route('/processes/[0-9a-z]+', self.handle_update, {'UPDATE'})
        self.run()

        self.expiration_greenlet = Greenlet.spawn(self.expiration_timer)
        self.expiration_greenlet.start()

        self.cluster = cluster
        self.address = address
        self.running_processes = {}
        self.enabled = True

        self.watcher_timeout = 5

    def expiration_timer(self):
        """Expire processes that have sent no updates for watcher_timeout seconds"""
        
        while True:
            expire_after = datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc()) - timedelta(seconds = self.watcher_timeout)
            for (processid, process) in self.running_processes.items():
                if process['last_update'] <  expire_after:
                    logger.warning('Process %s timed out ! Removing from running processes list.', processid)
                    del self.running_processes[processid]
            sleep(1)
    
    def handle_update(self, request):
        """Handle updates requests sent by the watchers"""

        match = re.match('/processes/([0-9a-z]+)', request.uri_path)
        processid = match.group(1)

        data = json.loads(request.body)

        # Set last update timestamp
        data['last_update'] = datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc())

        # Update the running process list with received data
        if self.running_processes.has_key(processid):
            logger.debug('Received update from process %s.', processid)
            self.running_processes[processid].update(data)
        else:
            logger.debug('Received update from NEW process %s. Adding to running processes list.', processid)
            self.running_processes[processid] = data
        
        # The task has finished, send the report to the leader
        if data.has_key('finished') and data['finished']:
            logger.info("Reporting process %s (task %s) execution report to leader", processid, data['task'])
            ret = self.cluster.query_node(self.cluster.leader, uri = '/tasks/%s/report' % data['task'], method = 'POST', body = data)
            if ret['code'] != 200:
                logger.error("Encountered an error while sending process %s (task %s) execution report. Leader returned %d.", processid, data['task'], ret['code'])
            # Remove from the running processes list
            del self.running_processes[processid]

        return HTTPReply(code = 204)

    def execute_task(self, task):
        """Spawn a watcher to run a task"""

        if not self.enabled:
            raise ExecutionDisabled()

        logger.info("Running task %s", task)
        execid = uuid.uuid1().hex
        MonetaWatcher.spawn(execid, task, self.cluster.config.get('tasks')[task], self.address)
        logger.debug('Watcher started for task %s: process ID %s', task, execid)

        return execid

    def is_process_running(self, process):
        return process in self.running_processes.keys()

    def kill(self, process):
        """Kill a running process"""
        try:
            os.kill(self.running_processes[process]['pid'], signal.SIGTERM)
        except KeyError:
            raise ProcessNotFound("Process %s not found" % (process))

    def kill_all(self):
        """Kill all running tasks"""

        logger.debug("Killing %d currently running tasks", len(self.running_processes))

        for process in self.running_processes.keys():
            try:
                self.kill(process)
            except ProcessNotFound:
                pass


            
