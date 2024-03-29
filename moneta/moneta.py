# -*- coding: utf-8 -*-



import uuid
import argparse
import logging, logging.config
import sys
import signal
from gevent.hub import signal as signal_handler
import yaml

from moneta.cluster import MonetaCluster
from moneta.manager import MonetaManager
from moneta.server import MonetaServer
from moneta.watcher import MonetaWatcher
from moneta.pluginregistry import get_plugin_registry

logger = logging.getLogger('moneta')

def run():
    """ Run Moneta """
    parser = argparse.ArgumentParser()
    parser.add_argument('--listen', nargs='?', default=None, help='Listen host:port')
    parser.add_argument('--zookeeper', nargs='+', default=None, help='Zookeeper hosts (list of host:port items)')
    parser.add_argument('--nodename', nargs='?', default=None, help='Node name')
    parser.add_argument('--pools', nargs='?', default=None, help='Comma separated list of pools')
    parser.add_argument('--logfile', nargs='?', default=None, help='Log file')
    parser.add_argument('--loglevel', nargs='?', default=None, help='Log level', choices = ['debug', 'info', 'warning', 'error', 'critical', 'fatal'])
    parser.add_argument('--logconfig', nargs='?', default=None, help='Logging configuration file (overrides --loglevel and --logfile)')
    parser.add_argument('--plugindir', nargs='?', default=None, help='Plugins directory')
    parser.add_argument('--plugins', nargs='+', default=None, help='Load plugin(s)')
    parser.add_argument('--config', nargs='?', default=None, help='Config file')
    parser.add_argument('--leader', dest='leader', action='store_true', help='Contend to leader elections')
    parser.add_argument('--no-leader', dest='leader', action='store_false', help='Do not contend to leader elections')
    parser.add_argument('--watcher', dest='watcher', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()

    # Local config
    if args.config:
        try:
            with open(args.config, 'r') as f:
                local_config = yaml.safe_load(f.read())
        except Exception as e:
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

    if args.logfile:
        if not 'log' in local_config:
            local_config['log'] = {}
        local_config['log']['file'] = args.logfile

    if args.loglevel:
        if not 'log' in local_config:
            local_config['log'] = {}
        local_config['log']['level'] = args.loglevel

    if args.logconfig:
        if not 'log' in local_config:
            local_config['log'] = {}
        local_config['log']['config'] = args.logconfig

    # Default values
    if not 'listen' in local_config or not local_config['listen']:
        local_config['listen'] = "127.0.0.1:32000"

    if not 'manager_listen' in local_config or not local_config['manager_listen']:
        local_config['manager_listen'] = "127.0.0.1:32001"

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

    if not 'leader' in local_config or local_config['leader'] not in (True, False):
        local_config['leader'] = True

    if not 'log' in local_config or not local_config['log']:
        local_config['log'] = { }

    if not 'level' in local_config['log'] or not local_config['log']['level']:
        local_config['log']['level'] = 'info'

    # Logging
    if 'file' in local_config['log']:
        logging.basicConfig(filename = local_config['log']['file'], format =  '%(asctime)s [%(process)d:%(name)s] %(levelname)s: %(message)s')
    else:
        logging.basicConfig(format =  '%(asctime)s [%(process)d:%(name)s] %(levelname)s: %(message)s')

    loglevel = {
        'debug': logging.DEBUG,
        'info': logging.INFO,
        'warning': logging.WARNING,
        'error': logging.ERROR,
        'critical': logging.CRITICAL,
        'fatal': logging.FATAL
    }[local_config['log']['level']]

    logger.setLevel(loglevel)

    if 'config' in local_config['log']:
        logging.config.fileConfig(local_config['log']['config'])

    logger.debug('Local config: %s', local_config)

    # Main
    if args.watcher:
        # Run in Watcher mode
        logger.debug('Starting in Watcher mode')
        watcher = MonetaWatcher(local_config['nodename'])
        watcher.run()
        sys.exit(0)

    try:
        logger.debug('Starting')

        # Signals
        def handle_clean_exit():
            """ Clean exit, currently running tasks will be left running """
            logger.info('Termination signal received.')
            sys.exit(0)
        signal_handler(signal.SIGTERM, handle_clean_exit)

        # Instanciate Cluster, Manager and Server
        cluster = MonetaCluster(local_config['nodename'], local_config['listen'], ','.join(local_config['zookeeper']), pools = local_config['pools'], contend_for_lead = local_config['leader'])
        manager = MonetaManager(cluster, local_config['manager_listen'])
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

    except SystemExit as e:
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
