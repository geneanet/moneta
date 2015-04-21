# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging

from datetime import datetime
import pytz
import json

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

        self.registry.register_hook('ReceivedReport', self.onReceivedReport)

    def onReceivedReport(self, report):
        """Store the report in ElasticSearch"""

        task = report['task']
        taskconfig = self.cluster.config['tasks'][task]

        report['task_name'] = taskconfig['name']
        if 'tags' in taskconfig:
            report['task_tags'] = taskconfig['tags']

        if self.cluster.config['elasticsearch_url']:
            logger.info("Sending report for task %s to ElasticSearch", task)

            report = report.copy()

            report['@timestamp'] = datetime.utcnow().replace(tzinfo = pytz.utc).isoformat()

            (addr, path, index) = self.cluster.get_elasticsearch_config()

            try:
                client = HTTPClient(addr)
                ret = client.request(HTTPRequest(uri = "%s%s/%s" % (path, index, 'moneta-task-report'), method = 'POST', body = json.dumps(report)))

                if ret.code > 400:
                    raise Exception("Unable to log in ElasticSearch: Response code %d (%s)" % (ret.code, ret.body))

            except Exception:
                raise Exception("Unable to log in ElasticSearch")            
