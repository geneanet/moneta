# -*- coding: utf-8 -*-



import logging
from moneta.http.http import HTTPReply
import re
from os.path import realpath

logger = logging.getLogger('moneta.plugins.gui')

def getDependencies():
    """ Return modules that need to be injected to the plugin constructor """
    return ['PluginRegistry', 'Server']

def init(config, registry, server):
    """ Instanciate the plugin """
    return GUIPlugin(config, registry,  server)

class GUIPlugin(object):
    """ GUI Plugin """

    def __init__(self, config, registry, server):
        """ Constructor """
        self.config = config
        self.registry = registry
        self.server = server

        self.server.register_route('/gui(/.*)?', self.handleGUI, {'GET'})

    def handleGUI(self, request):
        """Handle requests to /gui"""

        match = re.match(r'/gui(/.*)?', request.uri_path)
        uri = match.group(1)

        if not uri:
            return HTTPReply(code = 301, headers = {'Location': '/gui/'})
        
        if uri[-1:] == '/':
            uri = uri + 'index.html'

        docroot = realpath(self.config['docroot'])
        path = realpath(docroot + '/' + uri)

        if not path.startswith(docroot):
            return HTTPReply(code = 500, message='Requested file outside of docroot')

        try:
            fh = open(path, 'r')
            body = fh.read()
            return HTTPReply(body = body)

        except IOError as e:
            if e.errno == 2:
                return HTTPReply(code = 404)
            else:
                raise
