# -*- coding: utf-8 -*-

from __future__ import absolute_import

import uuid
import argparse
import logging

from moneta.cluster import MonetaCluster
from moneta.server import MonetaServer

def run():
    parser = argparse.ArgumentParser()
    parser.add_argument('--listen', nargs='?', default='127.0.0.1:32000', help='Listen host:port')
    parser.add_argument('--zookeeper', nargs='?', default='127.0.0.1:2181', help='Zookeeper hosts (comma-separated list of host:port items)')
    parser.add_argument('--nodename', nargs='?', default=uuid.uuid1().hex, help='Node name')
    parser.add_argument('--pool', nargs='?', default="default", help='Pool')
    parser.add_argument('--logfile', nargs='?', default=None, help='Log file')
    args = parser.parse_args()

    if args.logfile:
        logging.basicConfig(filename = args.logfile, format =  '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig()

    logging.getLogger('moneta').setLevel(logging.INFO)
    logging.getLogger('moneta.http').setLevel(logging.WARNING)

    logger = logging.getLogger('moneta')

    try:
        logger.debug('Starting')
        cluster = MonetaCluster(args.nodename, args.listen, args.zookeeper, pool = args.pool)
        server = MonetaServer(cluster, args.listen)
        logger.info('Started')

        server.run_forever()

    except BaseException:
        cluster.stop()
        logger.exception('An exception occurred. Terminating moneta.')
        exit(1)
