# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging
import json
from kazoo.exceptions import NoNodeError
from moneta.http.http import HTTPReply
import re

logger = logging.getLogger('moneta.plugins.executionsummary')

def getDependencies():
    return ['PluginRegistry', 'Cluster', 'Server']

def init(config, registry, cluster, server):
    return ExecutionSummaryPlugin(config, registry, cluster, server)

class ExecutionSummaryPlugin(object):
    def __init__(self, config, registry, cluster, server):
        self.registry = registry
        self.cluster = cluster
        self.server = server

        self.registry.register_hook('ReceivedReport', self.onReceivedReport)
        self.server.routes['/tasks/[0-9a-z]+/executionsummary'] = self.handleTaskRequest
        self.server.routes['/executionsummary'] = self.handleTasksRequest

    def handleTaskRequest(self, request):
        """Handle requests to /tasks/[0-9a-z]+/executionsummary"""

        match = re.match('/tasks/([0-9a-z]+)/executionsummary', request.uri_path)
        task = match.group(1)

        headers = { 'Content-Type': 'application/javascript' }

        if request.method == "GET":
            try:
                (summary, stat) = self.cluster.zk.get('/moneta/executionsummary/%s' % (task))
            except NoNodeError:
                summary = {}

            return HTTPReply(code = 200, body = summary, headers = headers)

        else:
            return HTTPReply(code = 405)

    def handleTasksRequest(self, request):
        """Handle requests to /executionsummary"""
        headers = { 'Content-Type': 'application/javascript' }

        if request.method == "GET":
            tasks = {}

            for task in self.cluster.config['tasks']:
                try:
                    (summary, stat) = self.cluster.zk.get('/moneta/executionsummary/%s' % (task))
                    summary = json.loads(summary)
                except NoNodeError:
                    summary = {}

                tasks[task] = summary

            return HTTPReply(code = 200, body = json.dumps(tasks), headers = headers)

        else:
            return HTTPReply(code = 405)

    def onReceivedReport(self, report):
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

        except Exception, e:
            logger.error('Cant update execution summary (%s)', str(e))

