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
        self.register_route('/cluster/config/.+', self.handle_cluster_config, {'GET', 'PUT', 'DELETE'})
        self.register_route('/node/[^/]+/.+', self.handle_node, {'GET', 'POST', 'PUT', 'DELETE', 'EXECUTE'})
        self.register_route('/status', self.handle_status, {'GET'})
        self.register_route('/tasks/[0-9a-z]+/running', self.handle_task_running, {'GET'})
        self.register_route('/tasks/[0-9a-z]+/processes', self.handle_task_processes, {'GET'})
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
            return HTTPReply(code = 200, headers = {"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, EXECUTE", "Access-Control-Allow-Headers": "content-type"} )

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

        except BaseException, e:
            logger.exception("Caught exception while handling request %s %s", request.method, request.uri)
            reply = HTTPReply(code = 500, body = json.dumps({"error": True, "message": repr(e), "traceback": traceback.format_exc()}), headers = { 'Content-Type': 'application/javascript' })

        reply.set_header("Access-Control-Allow-Origin", "*")

        return reply

    def handle_cluster_status(self, request):
        """Handle requests to /cluster/status"""
        """
        @api {get} /cluster/status Get cluster status
        @apiName GetClusterStatus
        @apiGroup Cluster
        @apiVersion 1.0.0

        @apiSuccess {Object}    nodes               Nodes in the cluster.
        @apiSuccess {Object}    nodes.node          Node.
        @apiSuccess {String[]}  nodes.node.pools    Pools in which the node is registered.
        @apiSuccess {String}    nodes.node.address  IP address of the node.
        @apiSuccess {String}    leader              Leader node.

        @apiSuccessExample {json} Example response:
            {
              "nodes": {
                "node1": {
                  "pools": ["pool1", "pool2"],
                  "address": "127.0.0.1:32001"
                },
                "node2": {
                  "pools": ["pool1"],
                  "address": "127.0.0.1:32002"
                },
                "node3": {
                  "pools": ["pool2"],
                  "address": "127.0.0.1:32003"
                },
              },
              "leader": "node1"
            }
        """

        headers = { 'Content-Type': 'application/javascript' }

        status  = {
            'nodes': self.cluster.nodes,
            'leader': self.cluster.leader
        }

        return HTTPReply(body = json.dumps(status), headers = headers)

    def handle_node(self, request):
        """Handle requests to /node/[^/]+/.+"""
        """
        @api {ANY} /node/:node/:uri Proxy a request
        @apiName ProxyToNode
        @apiGroup Misc
        @apiVersion 1.0.0

        @apiDescription Proxy the request :uri to the node :node, and forward the response.

        @apiParam {string}  :node    Node name.
        @apiParam {string}  :uri     URI.
        """

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
        """
        @api {get} /status Get node status
        @apiName GetNodeStatus
        @apiGroup Node
        @apiVersion 1.0.0

        @apiSuccess {Boolean}   execution_enabled                   Task execution is enabled on the node.
        @apiSuccess {Boolean}   leader                              Node is the leader.
        @apiSuccess {String}    name                                Node name.
        @apiSuccess {Boolean}   scheduler_running                   The scheduler is running on the node.
        @apiSuccess {String}    address                             Node IP address.
        @apiSuccess {String[]}  pools                               Pools in which the node is registered.
        @apiSuccess {Object}    running_processes                   Processes running on the host.
        @apiSuccess {Object}    running_processes.process           Process.
        @apiSuccess {String}    running_processes.process.started   Time the process started, ISO 8601 formatted.
        @apiSuccess {String}    running_processes.process.task      ID of the task.
        @apiSuccess {Boolean}   cluster_joined                      Node has joined the cluster.
        @apiSuccess {Boolean}   contending_for_lead                 Node is contending for lead.
        @apiSuccess {Boolean}   pools_joined                        Node has joined its pools.

        @apiSuccessExample {json} Example response:
            {
              "execution_enabled": true,
              "leader": false,
              "name": "node2",
              "scheduler_running": false,
              "address": "127.0.0.1:32002",
              "pools": ["pool1", "pool2"],
              "running_processes": {
                "b26e5cc2ef3f11e4817b0026b951c045": {
                  "started": "2015-04-30T13:49:18.351494+00:00",
                  "task": "508b4b72e44611e49e76c81f66cd0cca"
                }
              },
              "cluster_joined": true,
              "contending_for_lead": true,
              "pools_joined": true
            }
        """

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
        """
        @api {get} /cluster/pools Get cluster pools
        @apiName GetClusterPools
        @apiGroup Cluster
        @apiVersion 1.0.0

        @apiDescription List pools and nodes registered into each.

        @apiSuccess {String[]}  pool    List of nodes registered into the pool.

        @apiSuccessExample {json} Example response:
            {
              "pool1": ["node1", "node2"],
              "pool2: ["node1", "node3"]
            }
        """

        headers = { 'Content-Type': 'application/javascript' }

        return HTTPReply(body = json.dumps(self.cluster.pools), headers = headers)

    def handle_cluster_config(self, request):
        """Handle requests to /cluster/config/.+"""
        """
        @api {get} /cluster/config/:key Get cluster parameter
        @apiName GetClusterConfig
        @apiGroup Cluster
        @apiVersion 1.0.0

        @apiParam {string} :key  Name of the parameter to get
        """
        """
        @api {put} /cluster/config/:key Set cluster parameter
        @apiName SetClusterConfig
        @apiGroup Cluster
        @apiVersion 1.0.0

        @apiParam {string} :key  Name of the parameter to set
        """

        headers = { 'Content-Type': 'application/javascript' }

        match = re.match('/cluster/config/(.+)', request.uri_path)
        name = match.group(1)

        if request.method == "GET":
            try:
                return HTTPReply(body = json.dumps(self.cluster.config.get(name)), headers = headers)
            except KeyError:
                return HTTPReply(code = 404)

        elif request.method == "PUT":
            try:
                self.cluster.config.set(name, json.loads(request.body))
                return HTTPReply(code = 204)
            except (ValueError, TypeError) as error:
                return HTTPReply(code = 400, message = str(error))
            except KeyError:
                return HTTPReply(code = 404)

        elif request.method == "DELETE":
            try:
                self.cluster.config.clear(name)
                return HTTPReply(code = 204)
            except KeyError:
                return HTTPReply(code = 404)

    def handle_tags(self, request):
        """Handle requests to /tags"""
        """
        @api {get} /tags List tags
        @apiName GetTags
        @apiGroup Misc
        @apiVersion 1.0.0

        @apiDescription List currenty used tags

        @apiSuccessExample {json} Example response:
            [
              "tag1",
              "tag2"
            ]
        """

        headers = { 'Content-Type': 'application/javascript' }

        tags = []

        for task in self.cluster.config.get('tasks').itervalues():
            if 'tags' in task:
                tags += task['tags']

        tags = list(set(tags))

        return HTTPReply(code = 200, body = json.dumps(tags), headers = headers)

    def handle_plugins(self, request):
        """Handle requests to /plugins"""
        """
        @api {get} /plugins List plugins
        @apiName GetPlugins
        @apiGroup Node
        @apiVersion 1.0.0

        @apiDescription List plugins loaded on the node.

        @apiSuccessExample {json} Example response:
            [
              "configbackup",
              "mailer",
              "executionsummary"
            ]
        """

        headers = { 'Content-Type': 'application/javascript' }

        plugins = get_plugin_registry().get_plugins()
        return HTTPReply(code = 200, body = json.dumps(plugins), headers = headers)

    def handle_tasks(self, request):
        """Handle requests to /tasks"""
        """
        @api {get} /tasks List tasks
        @apiName GetTasks
        @apiGroup Tasks
        @apiVersion 1.0.0

        @apiDescription Return a list of all configured tasks, along with their configuration.

        @apiSuccessExample {json} Example response:
            {
              "021b2092ef4111e481a852540064e600": {
                  "name": "task 1",
                  "enabled": true,
                  "mode": "all",
                  "pools": ["web"],
                  "schedules": [
                    {"minute": ["*/5"]}
                  ],
                  "command": "/bin/task1",
              },
              "508b4b72e44611e49e76c81f66cd0cca": {
                  "name": "task 2",
                  "enabled": false,
                  "mode": "all",
                  "pools": ["pool2"],
                  "schedules": [
                    {"hours": [15], "minutes": [0]}
                  ],
                  "command": "/bin/task2",
              }
            }
        """
        """
        @api {post} /tasks Create a new task
        @apiName PostTasks
        @apiGroup Tasks
        @apiVersion 1.0.0

        @apiDescription Add a new task, providing its configuration.

        @apiParam {String}      name            Name.
        @apiParam {String}      description     Description.
        @apiParam {String[]}    tags            Tags.
        @apiParam {Boolean}     enabled         Task is enabled.
        @apiParam {String}      mode            Task mode ("any" or "all").
        @apiParam {String[]}    pools           Pools on which the task should run.
        @apiParam {Object[]}    schedules       Schedules at which the task should run.
        @apiParam {String}      command         Command to run.
        @apiParam {String}      workdir         Working directory.
        @apiParam {String}      user            User which the task will be run.
        @apiParam {String}      group           Group which the task will be run.
        @apiParam {Object}      env             Environment variables to set.
        @apiParam {String}      mailreport      If the mailer plugin is enabled, condition to send a report ("error", "stdout", "stderr", "output", "always").
        @apiParam {String[]}    mailto          If the mailer plugin is enabled, email addresses to send the reports to.

        @apiParamExample {json} Example parameters:
            {
              "name": "My task",
              "description": "Task description",
              "tags": ["tasg1", "tag2"],
              "enabled": true,
              "mode": "all",
              "pools": ["web"],
              "schedules": [
                {"minute": ["*/1"]}
              ],
              "command": "/bin/true",
              "workdir": "/tmp/",
              "user": "www-data",
              "group": "www-data",
              "env": {
                "MYENVVAR": "myvalue"
              },
              "mailreport": "output",
              "mailto": ["user@domain.org"]
            }

        @apiSuccess {Boolean}   created The task has been created.
        @apiSuccess {String}    id      ID of the newly created task.

        @apiSuccessExample {json} Example response:
            {
              "created": true,
              "id": "021b2092ef4111e481a852540064e600"
            }
        """
        """
        @api {delete} /tasks Delete all tasks
        @apiName DeleteTasks
        @apiGroup Tasks
        @apiVersion 1.0.0

        @apiDescription Delete all tasks. Use with caution.

        @apiSuccess {Boolean}   deleted     The tasks have been deleted.

        @apiSuccessExample {json} Example response:
            {
              "deleted": true
            }
        """

        headers = { 'Content-Type': 'application/javascript' }

        if request.method == "GET":
            tasks  = self.cluster.config.get('tasks')

            if 'tag' in request.args and request.args['tag']:
                tasks = dict( (taskid, task) for taskid, task in tasks.iteritems() if 'tags' in task and request.args['tag'] in task['tags'] )

            return HTTPReply(code = 200, body = json.dumps(tasks), headers = headers)

        elif request.method == "DELETE":
            oldtasks  = self.cluster.config.get('tasks')
            self.cluster.config.set('tasks', {})

            for (task, taskconfig) in oldtasks.iteritems():
                get_plugin_registry().call_hook('TaskDeleted', task, taskconfig)

            return HTTPReply(code = 204, body = json.dumps({"deleted": True}), headers = headers)

        elif request.method == "POST":
            task = uuid.uuid1().hex
            tasks = self.cluster.config.get('tasks')
            tasks[task] = json.loads(request.body)
            self.cluster.config.set('tasks', tasks)

            get_plugin_registry().call_hook('TaskCreated', task, tasks[task])

            return HTTPReply(code = 201, body = json.dumps({"id": task, "created": True}), headers = headers)

    def handle_task(self, request):
        """Handle requests to /tasks/[0-9a-z]+"""
        """
        @api {get} /tasks/:id Get a task
        @apiName GetTask
        @apiGroup Tasks
        @apiVersion 1.0.0

        @apiDescription Returns the configuration of a task.

        @apiParam {String}        :id             Task ID.

        @apiSuccess {String}      name            Name.
        @apiSuccess {String}      description     Description.
        @apiSuccess {String[]}    tags            Tags.
        @apiSuccess {Boolean}     enabled         Task is enabled.
        @apiSuccess {String}      mode            Task mode ("any" or "all").
        @apiSuccess {String[]}    pools           Pools on which the task should run.
        @apiSuccess {Object[]}    schedules       Schedules at which the task should run.
        @apiSuccess {String}      command         Command to run.
        @apiSuccess {String}      workdir         Working directory.
        @apiSuccess {String}      user            User which the task will be run.
        @apiSuccess {String}      group           Group which the task will be run.
        @apiSuccess {Object}      env             Environment variables to set.
        @apiSuccess {String}      mailreport      If the mailer plugin is enabled, condition to send a report ("error", "stdout", "stderr", "output", "always").
        @apiSuccess {String[]}    mailto          If the mailer plugin is enabled, email addresses to send the reports to.

        @apiSuccessExample {json} Example response:
            {
              "name": "My task",
              "description": "Task description",
              "tags": ["tasg1", "tag2"],
              "enabled": true,
              "mode": "all",
              "pools": ["web"],
              "schedules": [
                {"minute": ["*/1"]}
              ],
              "command": "/bin/true",
              "workdir": "/tmp/",
              "user": "www-data",
              "group": "www-data",
              "env": {
                "MYENVVAR": "myvalue"
              },
              "mailreport": "output",
              "mailto": ["user@domain.org"]
            }
        """
        """
        @api {put} /task/:id Update a task
        @apiName PutTask
        @apiGroup Tasks
        @apiVersion 1.0.0

        @apiDescription Update a task. Can also be used to create a task with a specific ID.

        @apiParam {String}      :id             Task ID.

        @apiParam {String}      name            Name.
        @apiParam {String}      description     Description.
        @apiParam {String[]}    tags            Tags.
        @apiParam {Boolean}     enabled         Task is enabled.
        @apiParam {String}      mode            Task mode ("any" or "all").
        @apiParam {String[]}    pools           Pools on which the task should run.
        @apiParam {Object[]}    schedules       Schedules at which the task should run.
        @apiParam {String}      command         Command to run.
        @apiParam {String}      workdir         Working directory.
        @apiParam {String}      user            User which the task will be run.
        @apiParam {String}      group           Group which the task will be run.
        @apiParam {Object}      env             Environment variables to set.
        @apiParam {String}      mailreport      If the mailer plugin is enabled, condition to send a report ("error", "stdout", "stderr", "output", "always").
        @apiParam {String[]}    mailto          If the mailer plugin is enabled, email addresses to send the reports to.

        @apiParamExample {json} Example parameters:
            {
              "name": "My task",
              "description": "Task description",
              "tags": ["tasg1", "tag2"],
              "enabled": true,
              "mode": "all",
              "pools": ["web"],
              "schedules": [
                {"minute": ["*/1"]}
              ],
              "command": "/bin/true",
              "workdir": "/tmp/",
              "user": "www-data",
              "group": "www-data",
              "env": {
                "MYENVVAR": "myvalue"
              },
              "mailreport": "output",
              "mailto": ["user@domain.org"]
            }

        @apiSuccess {Boolean}   updated The task has been updated.
        @apiSuccess {String}    id      ID of the task.

        @apiSuccessExample {json} Example response:
            {
              "updated": true,
              "id": "021b2092ef4111e481a852540064e600"
            }
        """
        """
        @api {delete} /task/:id Delete a task
        @apiName DeleteTask
        @apiGroup Tasks
        @apiVersion 1.0.0

        @apiDescription Delete a task.

        @apiParam {String}      :id             Task ID.

        @apiSuccess {Boolean}   deleted The task has been deleted.
        @apiSuccess {String}    id      ID of the task.

        @apiSuccessExample {json} Example response:
            {
              "deleted": true,
              "id": "021b2092ef4111e481a852540064e600"
            }
        """
        """
        @api {execute} /task/:id Execute a task
        @apiName ExecuteTask
        @apiGroup Tasks
        @apiVersion 1.0.1

        @apiDescription Execute a task.

        @apiParam {String}      :id             Task ID.
        @apiParam {String}      :target         Target for task execution ("local" to execute on the local node, otherwise execute on the nodes on which the task is configured to run).

        @apiSuccess {Boolean}   Executed The task has been executed.
        @apiSuccess {String}    id       ID of the task.

        @apiSuccessExample {json} Example response:
            {
              "deleted": true,
              "id": "021b2092ef4111e481a852540064e600"
            }
        """


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
            new = json.loads(request.body)
            if task in tasks:
                old = tasks[task]
            else:
                old = None

            tasks[task] = new
            self.cluster.config.set('tasks', tasks)

            if old:
                code = 204
                body = json.dumps({"id": task, "updated": True})
                get_plugin_registry().call_hook('TaskUpdated', task, old, new)
            else:
                code = 201
                body = json.dumps({"id": task, "created": True})
                get_plugin_registry().call_hook('TaskCreated', task, new)

            return HTTPReply(code = code, body = body)

        elif request.method == "DELETE":
            if task in tasks:
                old = tasks[task]
                del tasks[task]
                self.cluster.config.set('tasks', tasks)

                get_plugin_registry().call_hook('TaskDeleted', task, old)

                return HTTPReply(code = 204, body = json.dumps({"id": task, "deleted": True}), headers = headers)
            else:
                return HTTPReply(code = 404)

        if request.method == "EXECUTE":
            try:
                if 'target' in request.args and request.args['target'] == 'local':
                    self.manager.execute_task(task)
                else:
                    self.cluster.scheduler.run_task(task)

                return HTTPReply(code = 200, body = json.dumps({"id": task, "executed": True}))
            except ExecutionDisabled:
                return HTTPReply(code = 503, body = json.dumps({"id": task, "executed": False}))

    def handle_task_enable(self, request):
        """Handle requests to /tasks/[0-9a-z]+/(en|dis)able"""
        """
        @api {post} /task/:id/enable Enable a task
        @apiName EnableTask
        @apiGroup Tasks
        @apiVersion 1.0.0

        @apiParam {String}      :id             Task ID.

        @apiSuccess {Boolean}   updated The task has been updated.
        @apiSuccess {String}    id      ID of the task.

        @apiSuccessExample {json} Example response:
            {
              "updated": true,
              "id": "021b2092ef4111e481a852540064e600"
            }
        """
        """
        @api {post} /task/:id/disable Disable a task
        @apiName DisableTask
        @apiGroup Tasks
        @apiVersion 1.0.0

        @apiParam {String}      :id             Task ID.

        @apiSuccess {Boolean}   updated The task has been updated.
        @apiSuccess {String}    id      ID of the task.

        @apiSuccessExample {json} Example response:
            {
              "updated": true,
              "id": "021b2092ef4111e481a852540064e600"
            }
        """

        match = re.match('/tasks/([0-9a-z]+)/(en|dis)able', request.uri_path)
        task = match.group(1)
        action = match.group(2)

        enabled = (action == 'en')

        tasks = self.cluster.config.get('tasks')

        if task in tasks:
            code = 204

            old = tasks[task].copy()
            tasks[task]['enabled'] = enabled
            self.cluster.config.set('tasks', tasks)

            get_plugin_registry().call_hook('TaskUpdated', task, old, tasks[task])

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

    def handle_task_running(self, request):
        """Handle requests to /tasks/[0-9a-z]+/running"""
        """
        @api {get} /task/:id/running Check if a task is running
        @apiName IsTaskRunning
        @apiGroup Tasks
        @apiVersion 1.0.1

        @apiParam {String}      :id             Task ID.

        @apiSuccess {Boolean}   running The task is running.
        @apiSuccess {String}    id      ID of the task.

        @apiSuccessExample {json} Example response:
            {
              "running": true,
              "id": "021b2092ef4111e481a852540064e600"
            }
        """

        match = re.match('/tasks/([0-9a-z]+)/running', request.uri_path)
        task = match.group(1)

        running = self.cluster.is_task_running(task)

        headers = { 'Content-Type': 'application/javascript' }
        body = json.dumps({"id": task, "running": running})

        return HTTPReply(code = 200, body = body, headers = headers)

    def handle_task_processes(self, request):
        """Handle requests to /tasks/[0-9a-z]+/processes"""
        """
        @api {get} /task/:id/processes List running processes for a task
        @apiName ListTaskProcesses
        @apiGroup Tasks
        @apiVersion 1.0.1

        @apiParam {String}      :id             Task ID.

        @apiSuccessExample {json} Example response:
            {
                "021b2092ef4111e481a852540064e600" : {
                    "node": "node1",
                    "started": "2018-03-29T15:01:13.465183+00:00",
                    "task": "e4d07482e44711e49e76c81f66cd0cca"
                },
                "253a96e29868135d746989a6123f521e" : {
                    "node": "node2",
                    "started": "2018-03-29T14:01:13.352067+00:00",
                    "task": "508b4b72e44611e49e76c81f66cd0cca"
                },
                ...
            }
        """

        match = re.match('/tasks/([0-9a-z]+)/processes', request.uri_path)
        task = match.group(1)

        processes = self.cluster.list_task_processes(task)

        headers = { 'Content-Type': 'application/javascript' }
        body = json.dumps(processes)

        return HTTPReply(code = 200, body = body, headers = headers)
