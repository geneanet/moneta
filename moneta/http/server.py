# -*- coding: utf-8 -*-

from __future__ import absolute_import

from gevent.server import StreamServer
from gevent import sleep
import logging
from fcntl import fcntl, F_GETFD, F_SETFD, FD_CLOEXEC

from moneta.http.http import *

logger = logging.getLogger('moneta.http.server')

class HTTPServer(object):
    allowed_methods = [
        'OPTION',
        'GET',
        'HEAD',
        'POST',
        'PUT',
        'DELETE',
        'TRACE',
        'CONNECT'
    ]

    def __init__(self, address):
        self.address = address
        self.server = None

    @staticmethod
    def _set_cloexec(socket):
        """ Set the CLOEXEC attribute on a file descriptor """
        flags = fcntl(socket, F_GETFD)
        fcntl(socket, F_SETFD, flags | FD_CLOEXEC)

    def run(self):
        logger.debug("Listening on %s:%d", *self.address)
        self.server = StreamServer(self.address, self.handle_connection)
        self.server.start()
        self._set_cloexec(self.server.socket)

    def run_forever(self):
        self.run()

        while True:
            sleep(30)

    def handle_connection(self, socket, address):
        self._set_cloexec(self.server.socket)

        logger.debug("[%s:%d] Incoming connection", *address)

        fp = socket.makefile()

        keepalive = True

        while keepalive:
            # Query
            while True:
                line = fp.readline()

                if not line:
                    logger.debug("[%s:%d] Connection closed", *address)
                    return
                else:
                    line = line.strip()
                    if line:
                        break

            elements = line.split(" ")

            if len(elements) < 2 or len(elements) > 3 or not elements[1] or elements[0] not in self.allowed_methods:
                http_send_reply(socket, HTTPReply(code = 400, body = "<h1>Bad request</h1><pre>%s</pre>" % line))
                logger.error("Unable to parse request [%s]", line)
                continue
            else:
                method = elements[0]
                uri = elements[1]
                if len(elements) == 3:
                    version = elements[2]
                else:
                    version = None

            # Headers
            headers = {}

            while True:
                line = fp.readline()

                if not line:
                    logger.debug("[%s:%d] Connection closed", *address)
                    return
                else:
                    line = line.strip()
                    if line == "":
                        break

                try:
                    (header, data) = line.split(':', 1)
                    header = header.strip()
                    data = data.strip()
                    headers[header] = data
                except Exception:
                    http_send_reply(socket, HTTPReply(code = 400, body = "<h1>Unable to parse header line</h1><pre>%s</pre>" % line))
                    logger.warning("Unable to parse header line [%s]", line)
                    continue

            # Body
            body = ""

            if http_has_header(headers, 'content-length'):
                try:
                    bodylength = int(http_get_header(headers, 'content-length'))
                except Exception:
                    http_send_reply(socket, HTTPReply(code = 400, body = "<h1>Unable to parse content-length header</h1>"))
                    logger.warning("Unable to parse content-length header [%s]", http_get_header(headers, 'content-length'))
                    continue

                body = fp.read(bodylength)

            # Processing
            logger.info("[%s] Processing request %s %s", repr(address), method, uri)
            try:
                request = HTTPRequest(method, uri, version, headers, body)
                reply = self.handle_request(socket, address, request)
                http_send_reply(socket, reply)
            except BaseException, e:
                http_send_reply(socket, HTTPReply(code = 500))
                raise

            # Keep-alive
            if http_has_header(headers, 'connection'):
                if http_match_header(headers, 'connection', 'keep-alive'):
                    keepalive = True
                elif http_match_header(headers, 'connection', 'close'):
                    keepalive = False
            elif version == "HTTP/1.0":
                keepalive = False
            else:
                keepalive = True

        socket.close()
        logger.debug("[%s:%d] Connection closed", *address)

    def handle_request(self, socket, address, request):
        pass
