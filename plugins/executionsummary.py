# -*- coding: utf-8 -*-



import logging
from moneta import json
from kazoo.exceptions import NoNodeError
from moneta.http.http import HTTPReply
import re

logger = logging.getLogger('moneta.plugins.executionsummary')

def getDependencies():
    """ Return modules that need to be injected to the plugin constructor """
    return ['PluginRegistry', 'Cluster', 'Server']

def init(config, registry, cluster, server):
    """ Instanciate the plugin """
    return ExecutionSummaryPlugin(config, registry, cluster, server)

class ExecutionSummaryPlugin(object):
    """ ExecutionSummary Plugin """

    def __init__(self, config, registry, cluster, server):
        """ Constructor """
        self.registry = registry
        self.cluster = cluster
        self.server = server

        self.registry.register_hook('ReceivedReport', self.onReceivedReport)
        self.server.register_route('/tasks/[0-9a-z]+/executionsummary', self.handleTaskRequest, {'GET'})
        self.server.register_route('/executionsummary', self.handleTasksRequest, {'GET'})

    def handleTaskRequest(self, request):
        """Handle requests to /tasks/[0-9a-z]+/executionsummary"""

        match = re.match('/tasks/([0-9a-z]+)/executionsummary', request.uri_path)
        task = match.group(1)

        headers = {
            'Content-Type': 'application/javascript',
            'Access-Control-Allow-Origin': '*'
        }

        try:
            (summary, stat) = self.cluster.zk.get('/moneta/executionsummary/%s' % (task))
        except NoNodeError:
            summary = {}

        return HTTPReply(code = 200, body = summary, headers = headers)

    def handleTasksRequest(self, request):
        """Handle requests to /executionsummary"""
        headers = {
            'Content-Type': 'application/javascript',
            'Access-Control-Allow-Origin': '*'
        }

        tasks = {}

        for task in self.cluster.config.get('tasks'):
            try:
                (summary, stat) = self.cluster.zk.get('/moneta/executionsummary/%s' % (task))
                summary = json.loads(summary)
                tasks[task] = summary
            except NoNodeError:
                pass

        return HTTPReply(code = 200, body = json.dumps(tasks), headers = headers)

    def onReceivedReport(self, report):
        """Update the execution summary in Zookeeper"""
        try:
            task = report['task']
            summary = {
                'status': report['status'],
                'start_time': report['start_time'],
                'end_time': report['end_time'],
                'duration': report['duration']
            }

            logger.debug("Updating execution summary for task %s", task)

            try:
                self.cluster.zk.set('/moneta/executionsummary/%s' % (task), json.dumps(summary))
            except NoNodeError:
                self.cluster.zk.create('/moneta/executionsummary/%s' % (task), json.dumps(summary), makepath = True)

        except Exception as e:
            logger.error('Cant update execution summary (%s)', str(e))
