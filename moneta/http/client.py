# -*- coding: utf-8 -*-

from __future__ import absolute_import

from gevent.socket import socket
import logging

from moneta.http.http import *

logger = logging.getLogger('moneta.http.client')

class HTTPClient(object):
    def __init__(self, address):
        self.address = address
        self.socket = socket()
        self.connected = False

    def connect(self):
        self.socket.connect(self.address)
        self.connected = True

    def close(self):
        self.socket.close()
        self.connected = False

    def request(self, request):
        try:
            if not self.connected:
                self.connect()

            # Request
            http_send_request(self.socket, request)

            fp = self.socket.makefile()

            # Query
            line = fp.readline()

            if not line:
                raise Exception("Connection reset by peer")
            else:
                line = line.strip()

            elements = line.split(" ", 2)
            if len(elements) < 2 or elements[0][0:5] != "HTTP/" or not elements[1].isdigit():
                raise Exception("Unable to parse reply [%s]" % line)
            else:
                version = elements[0]
                code = int(elements[1])
                if len(elements) == 3:
                    message = elements[2]
                else:
                    message = ""

            # Headers
            headers = {}

            while True:
                line = fp.readline()

                if not line:
                    raise Exception("Connection reset by peer")
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
                    raise Exception("Unable to parse header line: [%s]" % line)

            # Body
            body = ""

            if http_has_header(headers, 'content-length'):
                try:
                    bodylength = int(http_get_header(headers, 'content-length'))
                except Exception:
                    raise Exception("Unable to parse content-length header: [%s]" % http_get_header(headers, 'content-length'))

                body = fp.read(bodylength)

                if bodylength > 0 and not body:
                    raise Exception("Connection reset by peer")

            elif http_match_header(headers, 'transfer-encoding', 'chunked'):
                while True:
                    chunkheader = fp.readline()

                    if not chunkheader:
                        raise Exception("Connection reset by peer")

                    try:
                        chunkheader = chunkheader.split(';')
                        chunksize = int(chunkheader[0], 16)
                    except Exception:
                        raise Exception("Unable to parse chunk header: [%s]" % chunkheader)

                    if chunksize == 0:
                        break

                    chunk = fp.read(chunksize + 2)
                    if not chunk:
                        raise Exception("Connection reset by peer")

                    body = body + chunk[:chunksize]

            else:
                while True:
                    bodypart = fp.read(4096)
                    if bodypart:
                        body = body + bodypart
                    else:
                        break

            # Keep-Alive
            if request.version == "HTTP/1.0" and not http_match_header(request.headers, 'connection', 'keep-alive'):
                self.close()

            # Processing
            return HTTPReply(version = version, code = code, message = message, headers = headers, body = body)

        except Exception:
            self.close()
            raise
