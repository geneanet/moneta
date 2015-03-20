# -*- coding: utf-8 -*-

from __future__ import absolute_import

from kazoo.client import KazooClient
from kazoo.handlers.gevent import SequentialGeventHandler
from kazoo.exceptions import NodeExistsError, NoNodeError

import json
from urlparse import urlparse
from datetime import datetime
import pytz
import logging

from moneta.scheduler import MonetaScheduler

logger = logging.getLogger('moneta.cluster')

class MonetaCluster(object):
    def __init__(self, nodename, addr, zkhosts, handler=SequentialGeventHandler(), pool = "default"):
        self.nodename = nodename
        self.addr = addr

        self.zk = KazooClient(zkhosts, handler = handler)
        self.zk.start()

        self.nodes = []
        self.pools = {}
        self.master = None
        self.config = {
            'tasks': {},
            'tick': 60,
            'email': None,
            'smtpserver': None,
            'elasticsearch_url': None,
            'elasticsearch_index': None,
            'elasticsearch_dateformat': None
        }

        self.electionticket = None

        try:
            self.zk.create('/moneta/nodes/%s' % self.nodename, json.dumps({ "address": self.addr, "pool": pool}), ephemeral = True, makepath = True)
        except NodeExistsError:
            raise Exception("Another node with the same ID already exists in the cluster.")

        try:
            self.zk.create('/moneta/pools/%s/%s' % (pool, self.nodename), self.addr, ephemeral = True, makepath = True)
        except NodeExistsError:
            raise Exception("Unable to join pool %s." % pool)

        try:
            self.zk.create('/moneta/config', json.dumps(self.config), makepath = True)
        except NodeExistsError:
            pass
        finally:
            self.zk.DataWatch("/moneta/config", self.handle_config_update)

        self.contend_for_lead()

    def contend_for_lead(self):
        self.electionticket = self.zk.create('/moneta/election/', self.nodename, ephemeral = True, sequence = True, makepath = True)
        self.zk.ChildrenWatch("/moneta/election", self._election_update)

    def stop(self):
        self.zk.stop()

    def _election_update(self, children):
        children.sort()

        oldmaster = self.master

        nodes = [self.zk.get("/moneta/election/%s" % child)[0] for child in children]
        self.master = nodes[0]

        self.handle_cluster_change()

        if oldmaster != self.master and self.master == self.nodename:
            self.handle_promotion()

    def handle_config_update(self, data, stat):
        logger.debug("Cluster config update")
        logger.debug("Cluster config : %s", data)
        self.config = json.loads(data)

    def handle_cluster_change(self):
        nodes = self.zk.get_children('/moneta/nodes')
        nodes = dict([ (node, json.loads(self.zk.get('/moneta/nodes/%s' % node)[0])) for node in nodes ])

        pools = {}
        for (node, nodeconf) in nodes.iteritems():
            pool = nodeconf['pool']
            if pool in pools:
                pools[pool].append(node)
            else:
                pools[pool] = [node]

        self.nodes = nodes
        self.pools = pools

        logger.info("Cluster change : %s", self.nodes)
        logger.info("Master : %s", self.master)

    def handle_promotion(self):
        logger.info("I am now the master. Starting scheduler.")
        scheduler = MonetaScheduler(self)
        scheduler.run()

    def update_last_tick(self, tick):
        try:
            self.zk.set('/moneta/last_tick', "%d" % tick)
        except NoNodeError:
            self.zk.create('/moneta/last_tick', "%d" % tick, makepath = True)

    def get_last_tick(self):
        try:
            (tick, stat) = self.zk.get('/moneta/last_tick')
            return int(tick)
        except NoNodeError:
            return None

    def update_config(self):
        self.zk.set('/moneta/config', json.dumps(self.config))

    def get_elasticsearch_config(self):
        url = urlparse(self.config['elasticsearch_url'])

        addr = (url.hostname, url.port)
        path = url.path

        if path[-1] != '/':
            path += '/'

        if self.config['elasticsearch_dateformat']:
            date = datetime.utcnow().replace(tzinfo = pytz.utc).strftime(self.config['elasticsearch_dateformat'])
        else:
            date = ""

        index = self.config['elasticsearch_index']
        index = index.replace('${date}', date)

        return (addr, path, index)