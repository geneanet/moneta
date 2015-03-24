# -*- coding: utf-8 -*-

from __future__ import absolute_import

import gevent
import time
from datetime import datetime
import random
import logging

from moneta.schedule import Schedule
from moneta.http.http import HTTPRequest, parse_host_port
from moneta.http.client import HTTPClient

logger = logging.getLogger('moneta.scheduler')

class MonetaScheduler(object):
    """ Schedule tasks to be run on cluster nodes """

    def __init__(self, cluster):
        self.cluster = cluster
        self.running = False

    def run(self):
        """ Start scheduler """
        self.running = True
        gevent.spawn(self.ticker)

    def stop(self):
        """ Stop scheduler """
        self.running = False

    def ticker(self):
        """ Method executed every /tick/ seconds when scheduler is running """
        if not self.running:
            return

        gevent.spawn_later(self.cluster.config['tick'], self.ticker)
        gevent.spawn(self.tick)

    def tick(self):
        """ Every tick, run jobs which had to be started between now and the last tick """

        this_tick = time.time()
        last_tick = self.cluster.get_last_tick()

        if not last_tick:
            last_tick = this_tick

        else:
            logger.debug("TICK: last tick %d seconds ago", (this_tick - last_tick))

            for (task_id, task_config) in self.cluster.config['tasks'].iteritems():
                should_run = False

                if not 'enabled' in task_config or not task_config['enabled']:
                    continue

                for schedule in [ Schedule(**schedule) for schedule in task_config['schedules'] ]:
                    if schedule.match_interval(datetime.fromtimestamp(last_tick), datetime.fromtimestamp(this_tick)):
                        should_run = True
                        break

                if should_run:
                    self.run_task(task_id)

        self.cluster.update_last_tick(this_tick)

    def  run_task(self, task):
        """ Run a job on the appropriate nodes """

        logger.info("Preparing to run task %s on appropriate nodes", task)

        task_config = self.cluster.config['tasks'][task]

        if 'pools' in task_config:
            pools = task_config['pools']
        else:
            pools = [ "default" ]

        nodes = []
        for pool in pools:
            if pool in self.cluster.pools:
                nodes += self.cluster.pools[pool]
            else:
                logger.warning("Task %s should run on pool %s but there is no such pool in the cluster.", task, pool)

        nodes = list(set(nodes))

        if 'mode' in task_config and task_config['mode'] == 'any':
            nodes = [ random.choice(nodes) ]

        if not nodes:
            logger.warning("There are no nodes to run task %s !", task)
            return

        for node in nodes:
            try:
                addr = parse_host_port(self.cluster.nodes[node]['address'])
                client = HTTPClient(addr)
                logger.info("Running task %s on node %s", task, node)
                ret = client.request(HTTPRequest(uri = '/tasks/%s' % task, method = 'EXECUTE'))
                if ret.code != 200:
                    logger.error ("Node %s answered %d when asked to execute task %s !", node, ret.code, task)
            except Exception:
                logger.exception("An exception occurred when trying to run task %s on node %s.", task, node)

