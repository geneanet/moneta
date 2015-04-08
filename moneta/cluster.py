# -*- coding: utf-8 -*-

from __future__ import absolute_import

from kazoo.client import KazooClient, KazooState
from kazoo.handlers.gevent import SequentialGeventHandler
from kazoo.exceptions import NodeExistsError, NoNodeError

import json
from urlparse import urlparse
from datetime import datetime
import pytz
import logging
import gevent

from moneta.scheduler import MonetaScheduler

logger = logging.getLogger('moneta.cluster')

class MonetaCluster(object):
    def __init__(self, nodename, addr, zkhosts, handler=SequentialGeventHandler(), pools = ["default"]):
        self.scheduler = MonetaScheduler(self)

        self.nodename = nodename
        self.addr = addr
        self.mypools = pools

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
        self.pools_watchers = {}

        self.cluster_joined = False
        self.pools_joined = False
        self.contending_for_lead = False

        self.is_master = False

        self.zk = KazooClient(zkhosts, handler = handler)

        # Watch for connection/disconnection to Zookeeper
        self.zk.add_listener(self._handle_connection_change)

        # Watch for config changes
        self.zk.DataWatch("/moneta/config", self._handle_config_update)

        self.zk.start()

    def start(self):
        try:
            self.join_cluster()
            self.join_pools()
            self.join_leader_election()

            if self.is_master:
                self.scheduler.run()
        except Exception:
            logger.exception("Exception encountered while starting cluster")
            exit(1)


    def stop(self):
        try:
            if self.is_master:
                self.scheduler.stop()

            self.quit_leader_election()
            self.quit_pools()
            self.quit_cluster()
        except Exception:
            logger.exception("Exception encountered while stopping cluster cluster")
            exit(1)

    def join_cluster(self):
        if self.cluster_joined:
            return

        logger.debug("Joining cluster")

        # Register node
        try:
            self.zk.create('/moneta/nodes/%s' % self.nodename, json.dumps({ "address": self.addr, "pools": self.mypools}), ephemeral = True, makepath = True)
            self.cluster_joined = True
            logger.info("Joined cluster")
        except NodeExistsError:
            self.cluster_joined = False
            raise Exception("Another node with the same ID already exists in the cluster.")

        # Watch for node changes
        self.zk.ChildrenWatch("/moneta/nodes", self._handle_nodes_update)

        # Watch for pool changes
        try:
            self.zk.create('/moneta/pools')
        except NodeExistsError:
            pass
        finally:
            self.pools_watchers = {}
            self.zk.ChildrenWatch("/moneta/pools", self._handle_pools_update)

        # Set default config if needed
        try:
            self.zk.create('/moneta/config', json.dumps(self.config), makepath = True)
            logger.info("No cluster config found, default valuess have been set.")
        except NodeExistsError:
            pass

    def quit_cluster(self):
        if not self.cluster_joined:
            return

        logger.debug("Quitting cluster")

        self.zk.delete('/moneta/nodes/%s' % self.nodename)
        self.cluster_joined = False

        logger.info("Quitted cluster")

    def join_pools(self):
        if self.pools_joined:
            return

        try:
            for pool in self.mypools:
                try:
                    logger.debug("Joining pool %s", pool)
                    self.zk.create('/moneta/pools/%s/%s' % (pool, self.nodename), self.addr, ephemeral = True, makepath = True)
                    logger.info("Joined pool %s", pool)
                except NodeExistsError:
                    raise Exception("Unable to join pool %s." % pool)
            self.pools_joined = True

        except Exception:
            self.pools_joined = False
            raise

    def quit_pools(self):
        if not self.pools_joined:
            return

        for pool in self.mypools:
            logger.debug("Quitting pool %s", pool)
            self.zk.delete('/moneta/pools/%s/%s' % (pool, self.nodename))
            logger.info("Quitted pool %s", pool)

        self.pools_joined = False

    def join_leader_election(self):
        if self.contending_for_lead:
            return

        logger.info("Contending for lead")
        self.electionticket = self.zk.create('/moneta/election/', self.nodename, ephemeral = True, sequence = True, makepath = True)
        self.zk.ChildrenWatch("/moneta/election", self._handle_election_update)
        self.contending_for_lead = True

    def quit_leader_election(self):
        if not self.contending_for_lead:
            return

        if self.scheduler.running:
            self.scheduler.stop()

        logger.info("Abandonning participation in leader election")
        self.zk.delete(self.electionticket)
        self.electionticket = None
        self.contending_for_lead = True

    def get_last_tick(self):
        try:
            (tick, stat) = self.zk.get('/moneta/last_tick')
            return int(tick)
        except NoNodeError:
            return None

    def update_last_tick(self, tick):
        try:
            self.zk.set('/moneta/last_tick', "%d" % tick)
        except NoNodeError:
            self.zk.create('/moneta/last_tick', "%d" % tick, makepath = True)

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

    def _handle_connection_change(self, state):
        if state == KazooState.LOST:
            logger.error("Zookeeper connection lost")

            self.pools_joined = False
            self.cluster_joined = False
            self.contending_for_lead = False
            self.is_master = False

            if self.scheduler.running:
                self.scheduler.stop()

        elif state == KazooState.SUSPENDED:
            logger.warning("Zookeeper connection suspended")

            if self.scheduler.running:
                self.scheduler.stop()

        else:
            logger.info("Zookeeper connection OK")
            gevent.spawn(self.start)

    def _handle_election_update(self, children):
        children.sort()

        nodes = [self.zk.get("/moneta/election/%s" % child)[0] for child in children]

        oldmaster = self.master

        if nodes:
            self.master = nodes[0]
        else:
            self.master = None

        if oldmaster != self.master:
            logger.info("Master change : %s", self.master)

        if not self.is_master and self.master == self.nodename:
            logger.info("I am now the master.")
            self.is_master = True
            self.scheduler.run()

    def _handle_config_update(self, data, stat):
        logger.debug("Cluster config update")
        logger.debug("Cluster config : %s", data)
        self.config = json.loads(data)

    def _handle_nodes_update(self, children):
        nodes = {}

        for child in children:
            try:
                nodes[child] = json.loads(self.zk.get('/moneta/nodes/%s' % child)[0])
            except NoNodeError:
                pass

        self.nodes = nodes

        logger.info("Cluster change : %s", self.nodes)

    def _handle_pools_update(self, pools):
        pools_watchers = {}

        for pool in pools:
            if pool in self.pools_watchers:
                pools_watchers[pool] = self.pools_watchers[pool]
            else:
                logger.debug("Watching pool %s for changes.", pool)

                def handle_pool_update(nodes, pool = pool):
                    logger.debug("Pool update %s: %s", pool, nodes)

                    if nodes:
                        self.pools[pool] = nodes
                    elif pool in self.pools:
                        del self.pools[pool]

                pools_watchers[pool] = self.zk.ChildrenWatch("/moneta/pools/%s" % pool, handle_pool_update)

        self.pools_watchers = pools_watchers