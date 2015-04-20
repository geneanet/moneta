# -*- coding: utf-8 -*-

from __future__ import absolute_import

import uuid
import argparse
import logging, logging.config
import sys
import signal
import gevent

from moneta.cluster import MonetaCluster
from moneta.manager import MonetaManager
from moneta.server import MonetaServer
from moneta.pluginregistry import get_plugin_registry

logger = logging.getLogger('moneta')
registry = get_plugin_registry()

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--listen', nargs='?', default='127.0.0.1:32000', help='Listen host:port')
    parser.add_argument('--zookeeper', nargs='?', default='127.0.0.1:2181', help='Zookeeper hosts (comma-separated list of host:port items)')
    parser.add_argument('--nodename', nargs='?', default=uuid.uuid1().hex, help='Node name')
    parser.add_argument('--pools', nargs='?', type=lambda s: s.split(','), default="default", help='Comma separated list of pools')
    parser.add_argument('--logfile', nargs='?', default=None, help='Log file')
    parser.add_argument('--loglevel', nargs='?', default="info", help='Log level', choices = ['debug', 'info', 'warning', 'error', 'critical', 'fatal'])
    parser.add_argument('--logconfig', nargs='?', default=None, help='Logging configuration file (overrides --loglevel and --logfile)')
    parser.add_argument('--plugindir', nargs='?', default='plugins', help='Plugins directory')
    parser.add_argument('--loadplugin', nargs='+', default=[], help='Load plugin(s)')
    args = parser.parse_args()

    # Logging
    if args.logfile:
        logging.basicConfig(filename = args.logfile, format =  '%(asctime)s [%(name)s] %(levelname)s: %(message)s')
    else:
        logging.basicConfig(format =  '%(asctime)s [%(name)s] %(levelname)s: %(message)s')

    loglevel = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL,
        'fatal': logging.FATAL
    }[args.loglevel]

    logger.setLevel(loglevel)

    if args.logconfig:
        logging.config.fileConfig(args.logconfig)

    # Signals
    def handle_sigterm():
        """ Dirty exit, currently running tasks will be killed """
        logger.info('Received SIGTERM.')
        manager.shutdown(kill = True)
        sys.exit(0)

    def handle_sigwinch():
        """ Clean exit, waiting for currently running tasks to finish """
        logger.info('Received SIGUSR1.')
        cluster.quit_pools()
        manager.shutdown()
        sys.exit(0)

    gevent.signal(signal.SIGTERM, handle_sigterm)
    gevent.signal(signal.SIGWINCH, handle_sigwinch)

    # Main
    try:
        logger.debug('Starting')
        cluster = MonetaCluster(args.nodename, args.listen, args.zookeeper, pools = args.pools)
        manager = MonetaManager(cluster)
        server = MonetaServer(cluster, manager, args.listen)

        registry.add_module('Cluster', cluster)
        registry.add_module('Manager', manager)
        registry.add_module('Server', server)

        registry.set_plugin_dir(args.plugindir)

        for plugin in args.loadplugin:
            registry.register_plugin(plugin)

        cluster.connect()

        logger.info('Started')

        server.run_forever()

    except SystemExit, e:
        logger.info('Termination requested.')
        cluster.stop()
        logger.info('Terminated.')
        sys.exit(e)

    except KeyboardInterrupt:
        logger.info('Termination requested by keyboard interrupt.')
        cluster.stop()
        logger.info('Terminated.')
        sys.exit(1)

    except BaseException:
        logger.exception('An exception occurred. Terminating moneta.')
        cluster.stop()
        logger.info('Terminated.')
        sys.exit(1)
