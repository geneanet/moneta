# -*- coding: utf-8 -*-

from __future__ import absolute_import

import uuid
import argparse
import logging, logging.config
import sys
import signal
import gevent
import yaml

from moneta.cluster import MonetaCluster
from moneta.manager import MonetaManager
from moneta.server import MonetaServer
from moneta.pluginregistry import get_plugin_registry

logger = logging.getLogger('moneta')

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--listen', nargs='?', default=None, help='Listen host:port')
    parser.add_argument('--zookeeper', nargs='+', default=None, help='Zookeeper hosts (list of host:port items)')
    parser.add_argument('--nodename', nargs='?', default=None, help='Node name')
    parser.add_argument('--pools', nargs='?', default=None, help='Comma separated list of pools')
    parser.add_argument('--logfile', nargs='?', default=None, help='Log file')
    parser.add_argument('--loglevel', nargs='?', default="info", help='Log level', choices = ['debug', 'info', 'warning', 'error', 'critical', 'fatal'])
    parser.add_argument('--logconfig', nargs='?', default=None, help='Logging configuration file (overrides --loglevel and --logfile)')
    parser.add_argument('--plugindir', nargs='?', default=None, help='Plugins directory')
    parser.add_argument('--plugins', nargs='+', default=None, help='Load plugin(s)')
    parser.add_argument('--config', nargs='?', default=None, help='Config file')
    parser.add_argument('--leader', dest='leader', action='store_true', help='Contend to leader elections')
    parser.add_argument('--no-leader', dest='leader', action='store_false', help='Do not contend to leader elections')
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

    def handle_sigquit():
        """ Dirty exit, currently running tasks will be left running """
        logger.info('Received SIGQUIT.')
        sys.exit(0)

    def handle_sigwinch():
        """ Clean exit, waiting for currently running tasks to finish """
        logger.info('Received SIGWINCH.')
        cluster.quit_pools()
        manager.shutdown()
        sys.exit(0)

    gevent.signal(signal.SIGTERM, handle_sigterm)
    gevent.signal(signal.SIGQUIT, handle_sigquit)
    gevent.signal(signal.SIGWINCH, handle_sigwinch)

    # Local config
    if args.config:
        try:
            with open(args.config, 'r') as f:
                local_config = yaml.safe_load(f.read())
        except Exception, e:
            raise Exception("Cant read config file %s (%s)", args.config, str(e))
    else:
        local_config = {}

    # Command line args override
    if args.listen:
        local_config['listen'] = args.listen

    if args.zookeeper:
        local_config['zookeeper'] = args.zookeeper

    if args.nodename:
        local_config['nodename'] = args.nodename

    if args.pools:
        local_config['pools'] = args.pools.split(',')

    if args.plugindir:
        if not 'plugins' in local_config:
            local_config['plugins'] = {}
        local_config['plugins']['path'] = args.plugindir

    if args.plugins:
        if not 'plugins' in local_config:
            local_config['plugins'] = {}
        local_config['plugins']['load'] = args.plugins

    if args.leader:
        local_config['leader'] = args.leader

    # Default values
    if not 'listen' in local_config or not local_config['listen']:
        local_config['listen'] = "127.0.0.1:32000"

    if not 'zookeeper' in local_config or not local_config['zookeeper']:
        local_config['zookeeper'] = ["127.0.0.1:2181"]

    if not 'nodename' in local_config or not local_config['nodename']:
        local_config['nodename'] = uuid.uuid1().hex

    if not 'pools' in local_config or not local_config['pools']:
        local_config['pools'] = ['default']

    if not 'plugins' in local_config or not local_config['plugins']:
        local_config['plugins'] = { }

    if not 'path' in local_config['plugins'] or not local_config['plugins']['path']:
        local_config['plugins']['path'] = "plugins"

    if not 'load' in local_config['plugins'] or not local_config['plugins']['load']:
        local_config['plugins']['load'] = []

    if not 'config' in local_config['plugins'] or not local_config['plugins']['config']:
        local_config['plugins']['config'] = {}

    if not 'leader' in local_config or not local_config['leader']:
        local_config['leader'] = True

    logger.debug('Local config: %s', local_config)

    # Main
    try:
        logger.debug('Starting')

        # Instanciate Cluster, Manager and Server
        cluster = MonetaCluster(local_config['nodename'], local_config['listen'], ','.join(local_config['zookeeper']), pools = local_config['pools'], contend_for_lead = local_config['leader'])
        manager = MonetaManager(cluster)
        server = MonetaServer(cluster, manager, local_config['listen'])

        # Load Plugins
        registry = get_plugin_registry()

        registry.add_module('Cluster', cluster)
        registry.add_module('Manager', manager)
        registry.add_module('Server', server)

        registry.set_plugin_dir(local_config['plugins']['path'])

        for plugin in local_config['plugins']['load']:
            if 'config' in local_config['plugins'] and plugin in local_config['plugins']['config']:
                registry.register_plugin(plugin, local_config['plugins']['config'][plugin])
            else:
                registry.register_plugin(plugin)

        # Connect to the Cluster
        cluster.connect()

        logger.info('Started')

        # Start the Server
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
