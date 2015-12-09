# -*- coding: utf-8 -*-

from __future__ import absolute_import

import logging
from imp import find_module, load_module

logger = logging.getLogger('moneta.pluginregistry')

class PluginRegistry(object):
    """ Plugins Registry  """

    def __init__(self, plugindir = "plugins", modules = None):
        """ Constructor """
        self.plugindir = plugindir
        self.plugins = {}

        if modules:
            self.modules = modules
        else:
            self.modules = {}

        self.modules['PluginRegistry'] = self

        self.hooks = {}
        self.filters = {}

    def register_plugin(self, plugin_name, config = None):
        """ Load a plugin """
        if config == None:
            config = {}

        try:
            (filehandle, filepath, description) = find_module(plugin_name, [ self.plugindir ])
            module = load_module(plugin_name, filehandle, filepath, description)

            dependencies = []
            for dependency in module.getDependencies():
                if dependency in self.modules:
                    dependencies.append(self.modules[dependency])
                else:
                    raise Exception("Required dependency %s not found." % dependency)

            self.plugins[plugin_name] = module.init(config, *dependencies)
        except Exception, e:
            raise Exception('Failed to load plugin %s (%s)' % (plugin_name, str(e)))
        else:
            logger.info('Loaded plugin %s', plugin_name)

    def register_hook(self, hook, function):
        """ Register a function on a hook """
        if hook in self.hooks:
            self.hooks[hook].append(function)
        else:
            self.hooks[hook] = [ function ]

    def register_filter(self, filter, function):
        """ Register a function on a filter hook """
        if filter in self.filters:
            self.filters[filter].append(function)
        else:
            self.filters[filter] = [ function ]

    def call_hook(self, hook, *args, **kwargs):
        """ Call the functions registered on a hook """
        if hook in self.hooks:
            for function in self.hooks[hook]:
                function(*args, **kwargs)

    def call_filter(self, filter, arg, context = None):
        """ Call the functions registered on a filter hook """
        arg = arg.copy()

        if filter in self.filters:
            for function in self.filters[filter]:
                arg = function(arg, context)

        return arg

    def set_plugin_dir(self, plugindir):
        """ Set the plugins directory """
        self.plugindir = plugindir

    def add_module(self, name, obj):
        """ Add a module that can be injected to plugins constructors """
        self.modules[name] = obj

    def get_plugins(self):
        """ Return a list of loaded plugins """
        return self.plugins.keys()


pluginregistry = PluginRegistry()

def get_plugin_registry():
    """ Return the plugin reggistry singleton """
    return pluginregistry
