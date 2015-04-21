# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging
import json
import yaml

logger = logging.getLogger('moneta.plugins.configbackup')

def getDependencies():
    return ['PluginRegistry']

def init(config, registry):
    return ConfigBackupPlugin(config, registry)

class ConfigBackupPlugin(object):
    def __init__(self, config, registry):
        if 'path' in config:
            self.path = config['path']
        else:
            raise Exception('Path must be specified')

        if 'format' in config:
            if config['format'] in ['json', 'yaml']:
                self.format = config['format']
            else:
                raise Exception('Format must be json or yaml')
        else:
            self.format = "json"

        self.registry = registry

        self.registry.register_hook('ConfigUpdated', self.onConfigUpdated)

    def onConfigUpdated(self, config):
        try:
            with open(self.path, 'w') as f:
                if self.format == 'json':
                    f.write(json.dumps(config))
                elif self.format == 'yaml':
                    f.write(yaml.safe_dump(config))
        except Exception, e:
            logger.error('Unable to backup configuration in format %s to file %s (%s)', self.format, self.path, str(e))