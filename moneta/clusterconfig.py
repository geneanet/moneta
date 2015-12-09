# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging

logger = logging.getLogger('moneta.clusterconfig')

class MonetaClusterConfig(object):
    """ Handles the configuration shared by all nodes in the cluster """

    def __init__(self, cluster):
        """ Constructor """
        self.cluster = cluster
        self.config = {}
        self.keys = {}

    def set_config(self, config):
        """ Set the whole config dict """
        self.config = config

    def get_config(self):
        """ Return the whole config dict """
        return self.config

    def create_key(self, key, default = None, validator = lambda value: True):
        """ Create a config key with an optional default value and validator function """
        if not key in self.keys:
            self.keys[key] = {'default': default, 'validator': validator}
        else:
            raise Exception('Key {0} is already defined.'.format(key))

    def get(self, key):
        """ Return the value of a config key  """
        if key in self.keys:
            if key in self.config:
                return self.config[key]
            else:
                return self.keys[key]['default']
        else:
            raise KeyError('Invalid property {0}.'.format(key))

    def set(self, key, value):
        """ Set the value of a config key  """
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
