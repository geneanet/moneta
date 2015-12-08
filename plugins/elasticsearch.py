# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging

import pytz
import json
from urlparse import urlparse
from datetime import datetime

from moneta.http.client import HTTPClient
from moneta.http.http import HTTPRequest

logger = logging.getLogger('moneta.plugins.elasticsearch')

def getDependencies():
    return ['PluginRegistry', 'Cluster']

def init(config, registry, cluster):
    return ElasticSearchPlugin(config, registry, cluster)

class ElasticSearchPlugin(object):
    def __init__(self, config, registry, cluster):
        self.config = config
        self.registry = registry
        self.cluster = cluster

        self.cluster.config.create_key('elasticsearch', {
            'url': None,
            'index': None,
            'dateformat': None
        })

        self.registry.register_hook('ReceivedReport', self.onReceivedReport)

    def get_elasticsearch_config(self):
        esconfig = self.cluster.config.get('elasticsearch')

        url = urlparse(esconfig['url'])

        addr = (url.hostname, url.port)
        path = url.path

        if path[-1] != '/':
            path += '/'

        if esconfig['dateformat']:
            date = datetime.utcnow().replace(tzinfo = pytz.utc).strftime(esconfig['dateformat'])
        else:
            date = ""

        index = esconfig['index']
        index = index.replace('${date}', date)

        return (addr, path, index)

    def onReceivedReport(self, report):
        """Store the report in ElasticSearch"""

        try:
            task = report['task']
            taskconfig = self.cluster.config.get('tasks')[task]

            report['task_name'] = taskconfig['name']
            if 'tags' in taskconfig:
                report['task_tags'] = taskconfig['tags']

            report['task_command'] = taskconfig['command']

            logger.info("Sending report for task %s to ElasticSearch", task)

            report = report.copy()

            report['@timestamp'] = datetime.utcnow().replace(tzinfo = pytz.utc).isoformat()

            (addr, path, index) = self.get_elasticsearch_config()

            client = HTTPClient(addr)
            ret = client.request(HTTPRequest(uri = "%s%s/%s" % (path, index, 'moneta-task-report'), method = 'POST', body = json.dumps(report)))

            if ret.code > 400:
                raise Exception("Unable to log in ElasticSearch: Response code %d (%s)" % (ret.code, ret.body))

        except Exception, e:
            logger.error('An error has been encountered while storing report in ElasticSearch (%s)', str(e))
