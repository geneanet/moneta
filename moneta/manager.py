# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging
from datetime import datetime
import pytz
from pwd import getpwnam
from grp import getgrnam
from os import setgid, setuid, setgroups, chdir, environ
import json

from gevent.subprocess import Popen
from subprocess import PIPE
from gevent import spawn

from moneta.http.client import HTTPClient
from moneta.http.http import HTTPRequest, parse_host_port

logger = logging.getLogger('moneta.manager')

class MonetaManager(object):
    """ Execute tasks, keeping log of what is running """

    def __init__(self, cluster):
        self.cluster = cluster
        self.running_tasks = []

    def execute_task(self, task):
        """Spawn a greenlet to execute a task"""
        spawn(self._execute_task, task)

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

            report.update({
                "status": status,
                "returncode": returncode,
                "stdout": stdout,
                "stderr": stderr
            })

        except Exception, e:
            logger.exception("Encountered an exception while running task %s", task)

            report.update({
                "status": "fail",
                "error": str(e)
            })

        finally:
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
