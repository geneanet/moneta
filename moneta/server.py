# -*- coding: utf-8 -*-

from __future__ import absolute_import

import json
from collections import OrderedDict
import re
import uuid

import traceback

import logging

from moneta.http.client import HTTPClient
from moneta.http.server import HTTPServer
from moneta.http.http import HTTPReply, HTTPRequest, parse_host_port
from moneta.exceptions import ExecutionDisabled
from moneta.pluginregistry import get_plugin_registry

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

    def __init__(self, cluster, manager, address):
        """ Constructor """
        HTTPServer.__init__(self, parse_host_port(address))

        self.cluster = cluster
        self.manager = manager

        self.routes = OrderedDict()

        self.register_route('/cluster/pools', self.handle_cluster_pools, {'GET'})
        self.register_route('/cluster/status', self.handle_cluster_status, {'GET'})
        self.register_route('/cluster/config/.+', self.handle_cluster_config, {'GET', 'PUT'})
        self.register_route('/node/[^/]+/.+', self.handle_node, {'GET', 'POST', 'PUT', 'DELETE', 'EXECUTE'})
        self.register_route('/status', self.handle_status, {'GET'})
        self.register_route('/tasks/[0-9a-z]+/report', self.handle_task_report, {'POST'})
        self.register_route('/tasks/[0-9a-z]+/(en|dis)able', self.handle_task_enable, {'POST'})
        self.register_route('/tasks/[0-9a-z]+', self.handle_task, {'GET', 'PUT', 'DELETE', 'EXECUTE'})
        self.register_route('/tasks', self.handle_tasks, {'GET', 'POST', 'DELETE'})
        self.register_route('/tags', self.handle_tags, {'GET'})
        self.register_route('/plugins', self.handle_plugins, {'GET'})

    def register_route(self, route, controller, methods = "GET"):
        """ Register a function to generate response for an HTTP query """
        if not hasattr(controller, '__call__'):
            raise TypeError("Controller must be callable")

        if isinstance(methods, (str, unicode)):
            methods = { methods }

        if not isinstance(methods, set):
            raise TypeError('Methods must be a string or a set')

        try:
            regex = re.compile("^%s$" % route)
        except Exception as e:
            raise ValueError('Unable to compile regex for route {0}'.format(route))

        for method in methods:
            logger.debug("Registering method %s for route %s", method, route)
            self.routes[(route, method)] = {
                'controller': controller,
                'regex':  regex
            }

    def handle_request(self, socket, address, request):
        """Handle a HTTP request, finding the right route"""

        # Fold multiple / in URL
        request.uri_path = re.sub(r'/+', r'/', request.uri_path)

        # Remove ending /
        request.uri_path = re.sub(r'(.)/$', r'\1', request.uri_path)

        if request.method == 'OPTIONS':
            return HTTPReply(code = 200, headers = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE", "Access-Control-Allow-Headers": "content-type"} )

        try:
            reply = HTTPReply(code = 404)

            for ((route, method), routeconfig) in self.routes.iteritems():
                match = routeconfig['regex'].match(request.uri_path)
                if match:
                    if request.method == method:
                        logger.debug('Matched route %s method %s', route, method)
                        reply = routeconfig['controller'](request)
                        break
                    else:
                        reply = HTTPReply(code = 405)

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
            'leader': self.cluster.leader
        }

        return HTTPReply(body = json.dumps(status), headers = headers)

    def handle_node(self, request):
        """Handle requests to /node/[^/]+/.+"""

        match = re.match('/node/([^/]+)(/.+)', request.uri_path)
        node = match.group(1)
        uri = match.group(2)

        if node not in self.cluster.nodes:
            return HTTPReply(code = 404, headers = { 'Content-Type': 'application/javascript' }, body = '{ "message": "Node not found" }')

        addr = parse_host_port(self.cluster.nodes[node]["address"])

        client = HTTPClient(addr)
        return client.request(HTTPRequest(uri = uri, method = request.method, body = request.body))

    def handle_status(self, request):
        """Handle requests to /status"""

        headers = { 'Content-Type': 'application/javascript' }

        status  = {
            'name': self.cluster.nodename,
            'address': self.cluster.addr,
            'pools': self.cluster.mypools,
            'leader': self.cluster.is_leader,
            'cluster_joined': self.cluster.cluster_joined,
            'pools_joined': self.cluster.pools_joined,
            'contending_for_lead': self.cluster.contending_for_lead,

            'execution_enabled': self.manager.enabled,
            'running_processes': dict([ (execid, { 'task': details['task'], 'started': details['started'].isoformat() }) for (execid, details) in self.manager.running_processes.iteritems() ]),

            'scheduler_running': self.cluster.scheduler.running
        }

        return HTTPReply(body = json.dumps(status), headers = headers)

    def handle_cluster_pools(self, request):
        """Handle requests to /cluster/pools"""

        headers = { 'Content-Type': 'application/javascript' }

        return HTTPReply(body = json.dumps(self.cluster.pools), headers = headers)

    def handle_cluster_config(self, request):
        """Handle requests to /cluster/config/.+"""

        headers = { 'Content-Type': 'application/javascript' }

        match = re.match('/cluster/config/(.+)', request.uri_path)
        name = match.group(1)

        if request.method == "GET":
            try:
                return HTTPReply(body = json.dumps(self.cluster.config.get(name)), headers = headers)
            except NameError:
                return HTTPReply(code = 404)

        elif request.method == "PUT":
            try:
                self.cluster.config.set(name, json.loads(request.body))
                return HTTPReply(code = 204)
            except (ValueError, TypeError) as error:
                return HTTPReply(code = 400, message = str(error))

    def handle_tags(self, request):
        """Handle requests to /tags"""

        headers = { 'Content-Type': 'application/javascript' }

        tags = []

        for task in self.cluster.config.get('tasks').itervalues():
            if 'tags' in task:
                tags += task['tags']

        tags = list(set(tags))

        return HTTPReply(code = 200, body = json.dumps(tags), headers = headers)

    def handle_plugins(self, request):
        """Handle requests to /plugins"""

        headers = { 'Content-Type': 'application/javascript' }

        plugins = get_plugin_registry().get_plugins()
        return HTTPReply(code = 200, body = json.dumps(plugins), headers = headers)

    def handle_tasks(self, request):
        """Handle requests to /tasks"""

        headers = { 'Content-Type': 'application/javascript' }

        if request.method == "GET":
            tasks  = self.cluster.config.get('tasks')

            if 'tag' in request.args and request.args['tag']:
                tasks = dict( (taskid, task) for taskid, task in tasks.iteritems() if 'tags' in task and request.args['tag'] in task['tags'] )

            return HTTPReply(code = 200, body = json.dumps(tasks), headers = headers)

        elif request.method == "DELETE":
            self.cluster.config.set('tasks', {})
            return HTTPReply(code = 204, body = json.dumps({"deleted": True}))

        elif request.method == "POST":
            task = uuid.uuid1().hex
            tasks = self.cluster.config.get('tasks')
            tasks[task] = json.loads(request.body)
            self.cluster.config.set('tasks', tasks)

            return HTTPReply(code = 201, body = json.dumps({"id": task, "created": True}))

    def handle_task(self, request):
        """Handle requests to /tasks/[0-9a-z]+"""

        headers = { 'Content-Type': 'application/javascript' }

        match = re.match('/tasks/([0-9a-z]+)', request.uri_path)
        task = match.group(1)

        tasks = self.cluster.config.get('tasks')

        if request.method == "GET":
            if task in tasks:
                return HTTPReply(code = 200, body = json.dumps(tasks[task]), headers = headers)
            else:
                return HTTPReply(code = 404)

        elif request.method == "PUT":
            if task in tasks:
                code = 204
                body = json.dumps({"id": task, "updated": True})
            else:
                code = 201
                body = json.dumps({"id": task, "created": True})

            tasks[task] = json.loads(request.body)

            self.cluster.config.set('tasks', tasks)

            return HTTPReply(code = code, body = body)

        elif request.method == "DELETE":
            if task in tasks:
                del tasks[task]
                self.cluster.config.set('tasks', tasks)
                return HTTPReply(code = 204, body = json.dumps({"id": task, "deleted": True}))
            else:
                return HTTPReply(code = 404)

        if request.method == "EXECUTE":
            try:
                self.manager.execute_task(task)
                return HTTPReply(code = 200, body = json.dumps({"id": task, "executed": True}))
            except ExecutionDisabled:
                return HTTPReply(code = 503, body = json.dumps({"id": task, "executed": False}))

    def handle_task_enable(self, request):
        """Handle requests to /tasks/[0-9a-z]+/(en|dis)able"""

        match = re.match('/tasks/([0-9a-z]+)/(en|dis)able', request.uri_path)
        task = match.group(1)
        action = match.group(2)

        enabled = (action == 'en')

        tasks = self.cluster.config.get('tasks')

        if task in tasks:
            code = 204

            tasks[task]['enabled'] = enabled
            self.cluster.config.set('tasks', tasks)

            headers = { 'Content-Type': 'application/javascript' }
            body = json.dumps({"id": task, "updated": True})

            return HTTPReply(code = code, body = body, headers = headers)
        else:
            return HTTPReply(code = 404)

    def handle_task_report(self, request):
        """Handle requests to /tasks/[0-9a-z]+/report"""

        match = re.match('/tasks/([0-9a-z]+)/report', request.uri_path)
        task = match.group(1)

        report = json.loads(request.body)
        logger.info("Received execution report for task %s", task)
        logger.debug("Execution report for task %s: %s", task, repr(report))

        get_plugin_registry().call_hook('ReceivedReport', report)

        return HTTPReply(code = 200)
