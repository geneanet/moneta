# -*- coding: utf-8 -*-

from __future__ import absolute_import

from kazoo.client import KazooClient, KazooState
from kazoo.handlers.gevent import SequentialGeventHandler
from kazoo.exceptions import NodeExistsError, NoNodeError

import json
import logging
import gevent

from moneta.scheduler import MonetaScheduler
from moneta.pluginregistry import get_plugin_registry
from moneta.clusterconfig import MonetaClusterConfig
from moneta.http.http import HTTPRequest, parse_host_port
from moneta.http.client import HTTPClient

logger = logging.getLogger('moneta.cluster')

class MonetaCluster(object):
    def __init__(self, nodename, addr, zkhosts, handler=SequentialGeventHandler(), pools = ["default"], contend_for_lead = True):
        """ Constructor """
        self.scheduler = MonetaScheduler(self)

        self.nodename = nodename
        self.addr = addr
        self.mypools = pools
        self.contend_for_lead = contend_for_lead

        self.nodes = []
        self.pools = {}
        self.leader = None

        self.config = MonetaClusterConfig(self)
        self.config.create_key('tasks', {})
        self.config.create_key('tick', 60)

        self.electionticket = None
        self.pools_watchers = {}

        self.cluster_joined = False
        self.pools_joined = False
        self.contending_for_lead = False

        self.is_leader = False

        self.zk = KazooClient(zkhosts, handler = handler)

        # Watch for connection/disconnection to Zookeeper
        self.zk.add_listener(self._handle_connection_change)

        # Watch for config changes
        self.zk.DataWatch("/moneta/config", self._handle_config_update)

    def connect(self):
        """ Connect to the zookeeper cluster """
        self.zk.start()

    def disconnect(self):
        """ Connect to the zookeeper cluster """
        self.zk.stop()

    def start(self):
        """ Start the Moneta cluster client: join cluster, pools, contend for lead if necessary """
        try:
            self.join_cluster()
            self.join_pools()

            if self.contend_for_lead:
                self.join_leader_election()

            if self.is_leader:
                self.scheduler.run()
        except Exception:
            logger.exception("Exception encountered while starting cluster")
            exit(1)


    def stop(self):
        """ Stop the Moneta cluster client: quit pools, leader election, cluster """
        try:
            if self.is_leader:
                self.scheduler.stop()

            self.quit_leader_election()
            self.quit_pools()
            self.quit_cluster()
        except Exception:
            logger.exception("Exception encountered while stopping cluster cluster")
            exit(1)

    def join_cluster(self):
        """ Join Moneta cluster: register node, set up config and pools change callbacks """
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
            self.zk.create('/moneta/config', json.dumps(self.config.get_config()), makepath = True)
            logger.info("No cluster config found, default valuess have been set.")
        except NodeExistsError:
            pass

    def quit_cluster(self):
        """ Quit moneta cluster """
        if not self.cluster_joined:
            return

        logger.debug("Quitting cluster")

        self.zk.delete('/moneta/nodes/%s' % self.nodename)
        self.cluster_joined = False

        logger.info("Quitted cluster")

    def join_pools(self):
        """ Join pools """
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
        """ Quit pools """
        if not self.pools_joined:
            return

        for pool in self.mypools:
            logger.debug("Quitting pool %s", pool)
            self.zk.delete('/moneta/pools/%s/%s' % (pool, self.nodename))
            logger.info("Quitted pool %s", pool)

        self.pools_joined = False

    def join_leader_election(self):
        """ Contend for lead """
        if self.contending_for_lead:
            return

        logger.info("Contending for lead")
        self.electionticket = self.zk.create('/moneta/election/', self.nodename, ephemeral = True, sequence = True, makepath = True)
        self.zk.ChildrenWatch("/moneta/election", self._handle_election_update)
        self.contending_for_lead = True

    def quit_leader_election(self):
        """ Quit leader election """
        if not self.contending_for_lead:
            return

        if self.scheduler.running:
            self.scheduler.stop()

        logger.info("Abandonning participation in leader election")
        self.zk.delete(self.electionticket)
        self.electionticket = None
        self.contending_for_lead = True

    def get_last_tick(self):
        """ Return the last time the scheduler was run on the cluster """
        try:
            (tick, stat) = self.zk.get('/moneta/last_tick')
            return float(tick)
        except NoNodeError:
            return None

    def update_last_tick(self, tick):
        """ Update the last time the scheduler was run on the cluster """
        try:
            self.zk.set('/moneta/last_tick', "%f" % tick)
        except NoNodeError:
            self.zk.create('/moneta/last_tick', "%f" % tick, makepath = True)

    def update_config(self, config):
        """ Update the cluster shared configuration """
        self.zk.set('/moneta/config', json.dumps(config))

    def _handle_connection_change(self, state):
        """ Handle Zookeeper connection events """
        if state == KazooState.LOST:
            logger.error("Zookeeper connection lost")

            self.pools_joined = False
            self.cluster_joined = False
            self.contending_for_lead = False
            self.is_leader = False

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
        """ Handle leader election events (node joined/quitted the election) """
        children.sort()

        nodes = [self.zk.get("/moneta/election/%s" % child)[0] for child in children]

        oldleader = self.leader

        if nodes:
            self.leader = nodes[0]
        else:
            self.leader = None

        if oldleader != self.leader:
            logger.info("Leader change : %s", self.leader)

        if not self.is_leader and self.leader == self.nodename:
            logger.info("I am now the leader.")
            self.is_leader = True
            self.scheduler.run()

    def _handle_config_update(self, data, stat):
        """ Handle the shared cluster configuration update """
        logger.debug("Cluster config update")
        logger.debug("Cluster config : %s", data)
        self.config.set_config(json.loads(data))
        get_plugin_registry().call_hook('ConfigUpdated', self.config)

    def _handle_nodes_update(self, children):
        """ Handle cluster nodes update (a node joined/quitted the cluster) """
        nodes = {}

        for child in children:
            try:
                nodes[child] = json.loads(self.zk.get('/moneta/nodes/%s' % child)[0])
            except NoNodeError:
                pass

        self.nodes = nodes

        logger.info("Cluster change : %s", self.nodes)

    def _handle_pools_update(self, pools):
        """ Handle cluster pools update (a node joined/quitted a pool) """
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

    def list_running_processes(self):
        """ Ask every node in the cluster for its status and return a summary of running processes """
        processes = {}

        for (nodename, node) in self.nodes.iteritems():
            logger.debug("Asking node %s for status", nodename)
            addr = parse_host_port(node['address'])
            client = HTTPClient(addr)
            response = client.request(HTTPRequest(uri = '/status'))
            if response.code == 200:
                status = json.loads(response.body)
                processes.update(status['running_processes'])
            else:
                raise Exception('Error while gathering status information from nodes. Node %s returned code %d.' % (nodename, response.code))

        return processes

    def list_running_tasks(self):
        """ List all tasks having at least one process currently running """
        tasks = set()
        processes = self.list_running_processes()
        
        for process in processes.itervalues():
            tasks.add(process['task'])
        return tasks

    def is_task_running(self, task):
        """ Check if a task is currently running on any node in the cluster """
        return task in self.list_running_tasks()
