# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging

logger = logging.getLogger('moneta.clusterconfig')

class MonetaClusterConfig(object):
    def __init__(self, cluster):
        self.cluster = cluster
        self.defaults = {}
        self.config = {}

    def set_config(self, config):
        self.config = config

    def get_config(self):
        return self.config

    def set_default(self, key, value):
        self.defaults[key] = value

    def get(self, key):
        if key in self.config:
            return self.config[key]
        elif key in self.defaults:
            return self.defaults[key]
        else:
            raise NameError('Property {0} is not defined and does not have a default value.')

    def set(self, key, value):
        self.config[key] = value
        self.cluster.update_config(self.config)
