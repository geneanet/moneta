# -*- coding: utf-8 -*-

from __future__ import absolute_import

import uuid
import argparse
import logging

from moneta.cluster import MonetaCluster
from moneta.server import MonetaServer

logger = logging.getLogger('moneta')

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--listen', nargs='?', default='127.0.0.1:32000', help='Listen host:port')
    parser.add_argument('--zookeeper', nargs='?', default='127.0.0.1:2181', help='Zookeeper hosts (comma-separated list of host:port items)')
    parser.add_argument('--nodename', nargs='?', default=uuid.uuid1().hex, help='Node name')
    parser.add_argument('--pools', nargs='?', type=lambda s: s.split(','), default="default", help='Comma separated list of pools')
    parser.add_argument('--logfile', nargs='?', default=None, help='Log file')
    parser.add_argument('--loglevel', nargs='?', default="info", help='Log level', choices = ['debug', 'info', 'warning', 'error', 'critical', 'fatal'])
    args = parser.parse_args()

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

    try:
        logger.debug('Starting')
        cluster = MonetaCluster(args.nodename, args.listen, args.zookeeper, pools = args.pools)
        server = MonetaServer(cluster, args.listen)
        logger.info('Started')

        server.run_forever()

    except BaseException:
        cluster.stop()
        logger.exception('An exception occurred. Terminating moneta.')
        exit(1)
