# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging

logger = logging.getLogger('moneta.clusterconfig')

class MonetaClusterConfig(object):
    def __init__(self, cluster):
        self.cluster = cluster
        self.config = {}
        self.keys = {}

    def set_config(self, config):
        self.config = config

    def get_config(self):
        return self.config

    def create_key(self, key, default = None, validator = lambda value: True):
        if not key in self.keys:
            self.keys[key] = {'default': default, 'validator': validator}
        else:
            raise Exception('Key {0} is already defined.'.format(key))

    def get(self, key):
        if key in self.keys:
            if key in self.config:
                return self.config[key]
            else:
                return self.keys[key]['default']
        else:
            raise KeyError('Invalid property {0}.'.format(key))

    def set(self, key, value):
        if key in self.keys:
            try:
                self.keys[key]['validator'](value)
                self.config[key] = value
                self.cluster.update_config(self.config)
            except ValueError as err:
                raise ValueError('Invalid format for property {0} (error: {1})'.format(key, str(err)))
            except TypeError as err:
                raise TypeError('Invalid type for property {0} (error: {1})'.format(key, str(err)))
        else:
            raise KeyError('Invalid property {0}.'.format(key))
