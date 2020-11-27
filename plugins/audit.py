# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging

import dateutil.tz
from moneta import json
import re
from urlparse import urlparse
from datetime import datetime
from dateutil import rrule

from moneta.http.client import HTTPClient
from moneta.http.http import HTTPRequest
from moneta.http.http import HTTPReply

logger = logging.getLogger('moneta.plugins.audit')

def getDependencies():
    """ Return modules that need to be injected to the plugin constructor """
    return ['PluginRegistry', 'Cluster', 'Server']

def init(config, registry, cluster, server):
    """ Instanciate the plugin """
    return AuditPlugin(config, registry, cluster, server)

class AuditPlugin(object):
    """ Audit Plugin """

    def __init__(self, config, registry, cluster, server):
        """ Constructor """
        self.config = config
        self.registry = registry
        self.cluster = cluster
        self.server = server

        self.cluster.config.create_key('audit', {
            'url': None,
            'index': None,
            'dateformat': None
        }, self.__validate_config)

        self.registry.register_hook('TaskCreated', self.onTaskCreated)
        self.registry.register_hook('TaskUpdated', self.onTaskUpdated)
        self.registry.register_hook('TaskDeleted', self.onTaskDeleted)
        self.registry.register_hook('TaskExecuted', self.onTaskExecuted)
        self.registry.register_hook('ReceivedReport', self.onReceivedReport)

        self.server.register_route('/auditlog', self.handleAuditLogRequest, {'GET'})
        self.server.register_route('/tasks/[0-9a-z]+/auditlog', self.handleAuditLogRequest, {'GET'})

    @staticmethod
    def __validate_config(config):
        """ Validate plugin configuration """
        if not isinstance(config, dict):
            raise TypeError('Value must be a dictionary')

        if not set(config.keys()).issubset(set(['url', 'index', 'dateformat'])):
            raise ValueError('Allowed keys are: url, index and dateformat')

        if not config['url'] or not config['index']:
            raise ValueError('Keys url and index must be specified')

    def __get_elasticsearch_config(self, dtfrom=None, dtuntil=None):
        """ Return a tuple (address, path, index) used to query the ES server """
        if not dtfrom:
            dtfrom = datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc())
        if not dtuntil:
            dtuntil = dtfrom

        if not isinstance(dtfrom, datetime):
            raise TypeError('dtfrom must be a datetime instance')
        if not isinstance(dtuntil, datetime):
            raise TypeError('dtuntil must be a datetime instance')

        if dtfrom > dtuntil:
            raise ValueError('Incorrect boundaries (from > until)')

        esconfig = self.cluster.config.get('audit')

        url = urlparse(esconfig['url'])

        addr = (url.hostname, url.port)
        path = url.path

        if path[-1] != '/':
            path += '/'

        if 'dateformat' in esconfig and esconfig['dateformat']:
            dates = list(rrule.rrule(rrule.HOURLY, dtstart=dtfrom, until=dtuntil))
            indices = set([ esconfig['index'].replace('${date}', date.strftime(esconfig['dateformat'])) for date in dates ])
            index = ",".join(indices)
        else:
            index = esconfig['index']

        if index == '':
            raise ValueError('Index name can not be empty')

        return (addr, path, index)

    def __send_elasticsearch_record(self, record):
        """ Send a new record to ES """
        (addr, path, index) = self.__get_elasticsearch_config()

        client = HTTPClient(addr)
        ret = client.request(HTTPRequest(uri = "%s%s/_doc/" % (path, index), method = 'POST', body = json.dumps(record), headers={'Content-Type': 'application/json'}))

        if ret.code > 400:
            raise Exception("Unable to log in ElasticSearch: Response code %d (%s)" % (ret.code, ret.body))

    def onTaskCreated(self, task, config):
        """ Hook called when a task is created """
        try:
            record = {
                'event_type': 'moneta-task-created',
                'task': task,
                '@timestamp': datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc()).isoformat(),
                '@level': 'info',
                'config': config
            }

            self.__send_elasticsearch_record(record)

        except Exception, e:
            logger.error('An error has been encountered while storing record in ElasticSearch (%s)', str(e))

    def onTaskUpdated(self, task, oldconfig, newconfig):
        """ Hook called when a task is updated """
        try:
            record = {
                'event_type': 'moneta-task-updated',
                'task': task,
                '@timestamp': datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc()).isoformat(),
                '@level': 'info',
                'config': newconfig,
                'oldconfig': oldconfig
            }

            self.__send_elasticsearch_record(record)

        except Exception, e:
            logger.error('An error has been encountered while storing record in ElasticSearch (%s)', str(e))

    def onTaskDeleted(self, task, config):
        """ Hook called when a task is deleted """
        try:
            record = {
                'event_type': 'moneta-task-deleted',
                'task': task,
                '@level': 'info',
                '@timestamp': datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc()).isoformat(),
                'config': config
            }

            self.__send_elasticsearch_record(record)

        except Exception, e:
            logger.error('An error has been encountered while storing record in ElasticSearch (%s)', str(e))

    def onTaskExecuted(self, task, node, success, message = ""):
        """ Hook called when the master has contacted a node to execute a task """
        try:
            record = {
                'event_type': 'moneta-task-execution',
                'task': task,
                '@timestamp': datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc()).isoformat(),
                'node': node,
                'success': success,
                'message': message
            }

            if (success):
                record['@level'] = 'success'
            else:
                record['@level'] = 'alert'

            self.__send_elasticsearch_record(record)

        except Exception, e:
            logger.error('An error has been encountered while storing record in ElasticSearch (%s)', str(e))

    def onReceivedReport(self, report):
        """ Hook called when the master has received an execution report """
        try:
            record = dict(report)
            task = record['task']
            taskconfig = self.cluster.config.get('tasks')[task]

            record['task_name'] = taskconfig['name']
            if 'tags' in taskconfig:
                record['task_tags'] = taskconfig['tags']
            record['task_command'] = taskconfig['command']

            record['@timestamp'] = datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc()).isoformat()

            if (record['status'] == 'ok'):
                record['@level'] = 'success'
            else:
                record['@level'] = 'alert'

            record['event_type'] = 'moneta-task-report'

            self.__send_elasticsearch_record(record)

        except Exception, e:
            logger.error('An error has been encountered while storing record in ElasticSearch (%s)', str(e))

    def handleAuditLogRequest(self, request):
        """Handle requests to /auditlog and /tasks/[0-9a-z]+/auditlog"""

        match = re.match('/tasks/([0-9a-z]+)/auditlog', request.uri_path)
        if match:
            task = match.group(1)
        else:
            task = None

        if 'from' in request.args:
            dtfrom = dateutil.parser.parse(request.args['from'])
        else:
            dtfrom = datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc())  - dateutil.relativedelta.relativedelta(days=1)

        if 'until' in request.args:
            dtuntil = dateutil.parser.parse(request.args['until'])
        else:
            dtuntil = datetime.utcnow().replace(tzinfo = dateutil.tz.tzutc())

        if 'limit' in request.args:
            limit = int(request.args['limit'])
        else:
            limit = 100

        if 'offset' in request.args:
            offset = int(request.args['offset'])
        else:
            offset = 0

        if 'level' in request.args:
            level = request.args['level'].split(',')
        else:
            level = None

        if 'type' in request.args:
            eventtype = request.args['type'].split(',')
        else:
            eventtype = None

        (addr, path, index) = self.__get_elasticsearch_config(dtfrom=dtfrom, dtuntil=dtuntil)

        uri = "%s%s/_search?ignore_unavailable=true&allow_no_indices=true&size=%d&from=%d" % (path, index, limit, offset)
        query = {
            "query": {
                "bool": {
                    "must": [],
                    "filter": [
                        {
                            "match_all": {}
                        },
                        {
                            "range": {
                                "@timestamp": {
                                "gte": dtfrom.isoformat(),
                                "lte": dtuntil.isoformat()
                            }
                        }
                        }
                    ],
                    "should": [],
                    "must_not": []
                }
            },
            "aggs": {
                "levels": {
                    "terms": {"field": "@level.keyword"}
                },
                "types": {
                    "terms": {"field": "event_type.keyword"}
                }
            },
            "sort": [
                {
                    "@timestamp": {
                        "order": "desc",
                        "unmapped_type": "boolean"
                    }
                }
            ],
            "post_filter": {
                "bool": { "must": [] }
            }
        }

        if task:
            query['query']['bool']['must'].append({ "term": { "task": { "value": task } } })

        if level:
            query['post_filter']['bool']['must'].append({ "terms": { "@level.keyword": level } })

        if eventtype:
            query['post_filter']['bool']['must'].append({ "terms": { "event_type.keyword": eventtype } })

        query = json.dumps(query)

        logger.debug("ES URL: %s%s/_search", path, index)
        logger.debug("ES Query:\n%s", query)

        client = HTTPClient(addr)
        answer = client.request(HTTPRequest(uri = uri, method = 'GET', body = query, headers = {'Content-Type': 'application/json'}))

        headers = {
            'Content-Type': 'application/javascript',
            'Access-Control-Allow-Origin': '*'
        }

        if answer.code == 200:
            data = json.loads(answer.body)
            hits = data['hits']['hits'] if 'hits' in data and 'hits' in data['hits'] else []
            count = data['hits']['total'] if 'hits' in data and 'total' in data['hits'] else 0
            records = []
            for hit in hits:
                record = hit['_source'].copy()
                record.update({
                    '@type': hit['_type']
                })
                records.append(record)
            levels = {}
            for bucket in data['aggregations']['levels']['buckets']:
                levels[bucket['key']] = bucket['doc_count']
            types = {}
            for bucket in data['aggregations']['types']['buckets']:
                types[bucket['key']] = bucket['doc_count']
            answer = {
                'from': dtfrom.isoformat(),
                'until': dtuntil.isoformat(),
                'limit': limit,
                'offset': offset,
                'count': count,
                'levels': levels,
                'types': types,
                'records': records
            }
            if task:
                answer['task'] = task
            return HTTPReply(code=200, body=json.dumps(answer), headers=headers)
        else:
            data = {
                "error": True,
                'message': 'ES query failed with error code %d' % answer.code,
                'es_answer': answer.body
            }
            return HTTPReply(code=500, body=json.dumps(data), headers=headers)
