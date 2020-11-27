# -*- coding: utf-8 -*-



import logging
from moneta import json
import yaml

logger = logging.getLogger('moneta.plugins.configbackup')

def getDependencies():
    """ Return modules that need to be injected to the plugin constructor """
    return ['PluginRegistry']

def init(config, registry):
    """ Instanciate the plugin """
    return ConfigBackupPlugin(config, registry)

class ConfigBackupPlugin(object):
    """ ConfigBackup Plugin """

    def __init__(self, config, registry):
        """ Constructor """
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
        """ Save the configuration to disk """
        try:
            with open(self.path, 'w') as f:
                if self.format == 'json':
                    f.write(json.dumps(config.get_config()))
                elif self.format == 'yaml':
                    f.write(yaml.safe_dump(config.get_config()))
        except Exception as e:
            logger.error('Unable to backup configuration in format %s to file %s (%s)', self.format, self.path, str(e))
