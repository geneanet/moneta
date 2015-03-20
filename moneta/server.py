# -*- coding: utf-8 -*-

from __future__ import absolute_import

import json
from collections import OrderedDict
import re
import uuid

from gevent.subprocess import Popen
from subprocess import PIPE
from gevent import spawn

from pwd import getpwnam
from grp import getgrnam
from os import setgid, setuid, setgroups, chdir, environ
from datetime import datetime

import traceback

from email.mime.text import MIMEText
import smtplib

from textwrap import dedent
import pytz

import logging
import urllib

from moneta.http.client import HTTPClient
from moneta.http.server import HTTPServer
from moneta.http.http import HTTPReply, HTTPRequest, parse_host_port

logger = logging.getLogger('moneta.server')

class MonetaServer(HTTPServer):
    """Moneta REST/HTTP server"""
    allowed_methods = [
        'GET',
        'POST',
        'PUT',
        'DELETE',
        'EXECUTE',
        'OPTIONS'
    ]

    def __init__(self, cluster, address):
        HTTPServer.__init__(self, parse_host_port(address))

        self.cluster = cluster

        self.routes = OrderedDict()

        self.routes['/cluster/pools'] = self.handle_cluster_pools
        self.routes['/cluster/status'] = self.handle_cluster_status
        self.routes['/cluster/config/.+'] = self.handle_cluster_config
        self.routes['/tasks/[0-9a-z]+/report'] = self.handle_task_report
        self.routes['/tasks/[0-9a-z]+/(en|dis)able'] = self.handle_task_enable
        self.routes['/tasks/[0-9a-z]+'] = self.handle_task
        self.routes['/tasks'] = self.handle_tasks
        self.routes['/tags'] = self.handle_tags

    def handle_request(self, socket, address, request):
        """Handle a request, finding the right route"""

        # Fold multiple / in URL
        request.uri_path = re.sub(r'/+', r'/', request.uri_path)

        # Remove ending /
        request.uri_path = re.sub(r'(.)/$', r'\1', request.uri_path)

        if request.method == 'OPTIONS':
            return HTTPReply(code = 200, headers = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE", "Access-Control-Allow-Headers": "content-type"} )

        try:
            reply = HTTPReply(code = 404)

            for route in self.routes:
                match = re.match("^%s$" % route, request.uri_path)
                if match:
                    reply = self.routes[route](request)
                    break

        except BaseException:
            logger.exception("Caught exception while handling request %s %s", request.method, request.uri)
            reply = HTTPReply(code = 500, body = json.dumps({"error": True, "message": traceback.format_exc()}))

        reply.set_header("Access-Control-Allow-Origin", "*")

        return reply

    def handle_cluster_status(self, request):
        """Handle requests to /cluster/status"""

        headers = { 'Content-Type': 'application/javascript' }

        status  = {
            'nodes': self.cluster.nodes,
            'master': self.cluster.master
        }

        if request.method == "GET":
            return HTTPReply(body = json.dumps(status), headers = headers)
        else:
            return HTTPReply(code = 405)

    def handle_cluster_pools(self, request):
        """Handle requests to /cluster/pools"""

        headers = { 'Content-Type': 'application/javascript' }

        if request.method == "GET":
            return HTTPReply(body = json.dumps(self.cluster.pools), headers = headers)
            
        else:
            return HTTPReply(code = 405)

    def handle_cluster_config(self, request):
        """Handle requests to /cluster/config/.+"""

        headers = { 'Content-Type': 'application/javascript' }

        match = re.match('/cluster/config/(.+)', request.uri_path)
        name = match.group(1)

        if request.method == "GET":
            if name in self.cluster.config:
                return HTTPReply(body = json.dumps(self.cluster.config[name]), headers = headers)
            else:
                return HTTPReply(code = 404)

        elif request.method == "PUT":
            if name in self.cluster.config:
                code = 204
            else:
                code = 201

            self.cluster.config[name] = json.loads(request.body)
            self.cluster.update_config()

            return HTTPReply(code = code)

        else:
            return HTTPReply(code = 405)

    def handle_tags(self, request):
        """Handle requests to /tags"""

        headers = { 'Content-Type': 'application/javascript' }

        if request.method == "GET":
            tags = []

            for task in self.cluster.config['tasks'].itervalues():
                if 'tags' in task:
                    tags += task['tags']

            tags = list(set(tags))

            return HTTPReply(code = 200, body = json.dumps(tags), headers = headers)

        else:
            return HTTPReply(code = 405)


    def handle_tasks(self, request):
        """Handle requests to /tasks"""

        headers = { 'Content-Type': 'application/javascript' }

        if request.method == "GET":
            tasks  = self.cluster.config['tasks']

            if 'tag' in request.args and request.args['tag']:
                tasks = dict( (taskid, task) for taskid, task in tasks.iteritems() if 'tags' in task and request.args['tag'] in task['tags'] )

            return HTTPReply(code = 200, body = json.dumps(tasks), headers = headers)

        if request.method == "DELETE":
            self.cluster.config['tasks']= {}
            self.cluster.update_config()
            return HTTPReply(code = 204, body = json.dumps({"deleted": True}))

        elif request.method == "POST":
            task = uuid.uuid1().hex
            self.cluster.config['tasks'][task] = json.loads(request.body)
            self.cluster.update_config()

            return HTTPReply(code = 201, body = json.dumps({"id": task, "created": True}))

        else:
            return HTTPReply(code = 405)

    def handle_task(self, request):
        """Handle requests to /tasks/[0-9a-z]+"""

        headers = { 'Content-Type': 'application/javascript' }

        match = re.match('/tasks/([0-9a-z]+)', request.uri_path)
        task = match.group(1)

        if request.method == "GET":
            if task in self.cluster.config['tasks']:
                return HTTPReply(code = 200, body = json.dumps(self.cluster.config['tasks'][task]), headers = headers)
            else:
                return HTTPReply(code = 404)

        elif request.method == "PUT":
            if task in self.cluster.config['tasks']:
                code = 204
                body = json.dumps({"id": task, "updated": True})
            else:
                code = 201
                body = json.dumps({"id": task, "created": True})

            self.cluster.config['tasks'][task] = json.loads(request.body)
            self.cluster.update_config()

            return HTTPReply(code = code, body = body)

        elif request.method == "DELETE":
            if task in self.cluster.config['tasks']:
                del self.cluster.config['tasks'][task]
                self.cluster.update_config()
                return HTTPReply(code = 204, body = json.dumps({"id": task, "deleted": True}))
            else:
                return HTTPReply(code = 404)

        if request.method == "EXECUTE":
            spawn(self.execute_task, task)
            return HTTPReply(code = 200, body = json.dumps({"id": task, "executed": True}))

        else:
            return HTTPReply(code = 405)

    def handle_task_enable(self, request):
        """Handle requests to /tasks/[0-9a-z]+/(en|dis)able"""

        match = re.match('/tasks/([0-9a-z]+)/(en|dis)able', request.uri_path)
        task = match.group(1)
        action = match.group(2)

        enabled = (action == 'en')

        if request.method == "POST":
            if task in self.cluster.config['tasks']:
                code = 204

                self.cluster.config['tasks'][task]['enabled'] = enabled
                self.cluster.update_config()

                headers = { 'Content-Type': 'application/javascript' }
                body = json.dumps({"id": task, "updated": True})

                return HTTPReply(code = code, body = body, headers = headers)
            else:
                return HTTPReply(code = 404)

        else:
            return HTTPReply(code = 405)

    def handle_task_report(self, request):
        """Handle requests to /tasks/[0-9a-z]+/report"""

        match = re.match('/tasks/([0-9a-z]+)/report', request.uri_path)
        task = match.group(1)

        if request.method == "POST":
            report = json.loads(request.body)
            logger.info("Received execution report for task %s", task)
            logger.debug("Execution report for task %s: %s", task, repr(report))

            taskconfig = self.cluster.config['tasks'][task]

            if 'mailreport' in taskconfig and ((taskconfig['mailreport'] == 'error' and report['status'] != 'ok') or taskconfig['mailreport'] == 'always'):
                self.mail_report(task, report)

            if self.cluster.config['elasticsearch_url']:
                self.log_elasticsearch('moneta-task-report', report)

            taskconfig['last_report'] = {
                'status': report['status'],
                'start_time': report['start_time'],
                'end_time': report['end_time'],
                'duration': report['duration']
            }
            self.cluster.update_config()

            return HTTPReply(code = 200)

        else:
            return HTTPReply(code = 405)

    def log_elasticsearch(self, documenttype, data):
        data = data.copy()

        data['@timestamp'] = datetime.utcnow().replace(tzinfo = pytz.utc).isoformat()

        (addr, path, index) = self.cluster.get_elasticsearch_config()

        try:
            client = HTTPClient(addr)
            ret = client.request(HTTPRequest(uri = "%s%s/%s" % (path, index, documenttype), method = 'POST', body = json.dumps(data)))

            if ret.code > 400:
                raise Exception("Unable to log in ElasticSearch: Response code %d (%s)" % (ret.code, ret.body))

        except Exception:
            raise Exception("Unable to log in ElasticSearch")

    def mail_report(self, task, report):
        """Send a report by email"""

        taskconfig = self.cluster.config['tasks'][task]

        if not self.cluster.config['smtpserver']:
            raise Exception("An email report should be delivered for task %s, but no smtp server has been configured.")

        if not self.cluster.config['email']:
            raise Exception("An email report should be delivered for task %s, but no sender email has been configured.")

        if not 'mailto' in taskconfig or not taskconfig['mailto']:
            raise Exception("An email report should be delivered for task %s, but the task has no mailto parameter or mailto is empty.")

        # Template

        msgbody = dedent(
            u"""\
            Task: {task[name]}
            Description: {task[description]}
            -------------------------------------------------------------------------------
            Status: {report[status]}
            Executed on node: {report[node]}
            Started: {report[start_time]}
            Ended: {report[end_time]}
            Duration: {report[duration]} seconds
            -------------------------------------------------------------------------------
            """)

        if report['status'] == "fail":
            msgbody += "Error: {report[error]}\n"
        else:
            msgbody += "Return code: {report[returncode]}\n"

            if report['stdout']:
                msgbody += dedent(
                    """\

                    stdout :
                    -------------------------------------------------------------------------------
                    {report[stdout]}
                    -------------------------------------------------------------------------------
                    """)

            if report['stderr']:
                msgbody += dedent(
                    """\

                    stderr :
                    -------------------------------------------------------------------------------
                    {report[stderr]}
                    -------------------------------------------------------------------------------
                    """)

        # Message

        msg = MIMEText(msgbody.format(task = taskconfig, report = report), "plain", "utf-8")

        mailto = taskconfig['mailto']
        if isinstance(mailto, str) or isinstance(mailto, unicode):
            mailto = [ mailto ]

        msg['Subject'] = u"Moneta Execution Report - Task %s" % taskconfig['name']
        msg['From'] = self.cluster.config['email']
        msg['To'] = ",".join(mailto)

        # Send

        s = smtplib.SMTP(self.cluster.config['smtpserver'])
        s.sendmail(self.cluster.config['email'], mailto, msg.as_string())
        s.quit()

    def execute_task(self, task):
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
