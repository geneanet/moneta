# -*- coding: utf-8 -*-



import gevent
import time
from datetime import datetime
import random
import logging

from moneta.schedule import Schedule
from moneta.http.http import HTTPRequest, parse_host_port
from moneta.http.client import HTTPClient
from moneta.pluginregistry import get_plugin_registry

logger = logging.getLogger('moneta.scheduler')

class MonetaScheduler(object):
    """ Schedule tasks to be run on cluster nodes """

    def __init__(self, cluster):
        """ Constructor """
        self.cluster = cluster
        self.running = False

        self.greenlet = None

    def run(self):
        """ Start scheduler """
        if self.running:
            return

        logger.info("Starting scheduler.")
        self.greenlet = gevent.spawn(self.ticker)
        self.running = True

    def stop(self):
        """ Stop scheduler """
        if not self.running:
            return

        logger.info("Stopping scheduler.")
        self.greenlet.kill()
        self.running = False

    def ticker(self):
        """ Method executed every /tick/ seconds when scheduler is running """

        gevent.spawn(self.tick)
        self.greenlet = gevent.spawn_later(self.cluster.config.get('tick'), self.ticker)

    def tick(self):
        """ Run jobs which had to be started between now and the last tick """

        try:
            this_tick = time.time()
            last_tick = self.cluster.get_last_tick()

            if not last_tick:
                last_tick = this_tick

            else:
                logger.debug("TICK: last tick %d seconds ago (current interval %s to %s)", (this_tick - last_tick), datetime.fromtimestamp(last_tick).strftime("%H:%M:%S.%f"), datetime.fromtimestamp(this_tick).strftime("%H:%M:%S.%f"))

                for (task_id, task_config) in self.cluster.config.get('tasks').items():
                    should_run = False

                    try:
                        if not 'enabled' in task_config or not task_config['enabled']:
                            continue

                        for schedule in [ Schedule(**schedule) if schedule else Schedule() for schedule in task_config['schedules'] ]:
                            if schedule.match_interval(datetime.fromtimestamp(last_tick), datetime.fromtimestamp(this_tick)):
                                should_run = True
                                break
                    except Exception as e:
                        logger.exception("Encountered an exception while trying to match task %s schedules with current tick (TICK %d). The task may not be scheduled correctly.", task_id, this_tick)

                    if should_run:
                        gevent.spawn(self.run_task, task_id)

            self.cluster.update_last_tick(this_tick)

        except Exception as e:
            logger.exception("Encountered an exception in ticker (TICK %d). Some schedules may have been missed.", this_tick)

    def  run_task(self, task, ignore_concurrency = False):
        """ Run a job on the appropriate nodes """

        logger.info("Preparing to run task %s on appropriate nodes", task)

        try:
            task_config = self.cluster.config.get('tasks')[task]
            enforce_concurrency = 'concurrency' in task_config and task_config['concurrency'] > 0 and not ignore_concurrency

            if enforce_concurrency:
                # Count currently running processes
                running_processes_count = len(self.cluster.list_task_processes(task))

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

            if not nodes:
                logger.warning("There are no nodes to run task %s !", task)
                return

            if 'mode' in task_config and task_config['mode'] == 'any':
                nodes = [ random.choice(nodes) ]

            for node in nodes:
                try:
                    if enforce_concurrency and running_processes_count >= task_config['concurrency']:
                        logger.warning("Maximum concurrency reached (%d) for task %s !", task_config['concurrency'], task)
                        break

                    addr = parse_host_port(self.cluster.nodes[node]['address'])
                    client = HTTPClient(addr)
                    logger.info("Running task %s on node %s", task, node)
                    ret = client.request(HTTPRequest(uri = '/tasks/%s?target=local' % task, method = 'EXECUTE'))

                    get_plugin_registry().call_hook('TaskExecuted', task, node, ret.code == 200, ret.body)

                    if ret.code == 200:
                        if enforce_concurrency:
                            running_processes_count += 1
                    else:
                        logger.error ("Node %s answered %d when asked to execute task %s !", node, ret.code, task)

                except Exception:
                    logger.exception("An exception occurred when trying to run task %s on node %s.", task, node)

        except Exception as e:
            logger.exception("Encountered an exception while preparing to run task %s.", task)
