# -*- coding: utf-8 -*-

from __future__ import absolute_import

import re
import urllib

ErrorCodes = {
    100: "Continue",
    101: "Switching Protocols",
    200: "OK",
    201: "Created",
    202: "Accepted",
    203: "Non-Authoritative Information",
    204: "No Content",
    205: "Reset Content",
    206: "Partial Content",
    300: "Multiple Choices",
    301: "Moved Permanently",
    302: "Found",
    303: "See Other",
    304: "Not Modified",
    305: "Use Proxy",
    307: "Temporary Redirect",
    400: "Bad Request",
    401: "Unauthorized",
    402: "Payment Required",
    403: "Forbidden",
    404: "Not Found",
    405: "Method Not Allowed",
    406: "Not Acceptable",
    407: "Proxy Authentication Required",
    408: "Request Time-out",
    409: "Conflict",
    410: "Gone",
    411: "Length Required",
    412: "Precondition Failed",
    413: "Request Entity Too Large",
    414: "Request-URI Too Large",
    415: "Unsupported Media Type",
    416: "Requested range not satisfiable",
    417: "Expectation Failed",
    500: "Internal Server Error",
    501: "Not Implemented",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Time-out",
    505: "HTTP Version not supported"
}

def parse_host_port(addr, default_port = None):
    m = re.search(r'^(?P<host>.+?)(:(?P<port>[0-9]+))?$', addr)

    try:
        host = m.group('host')
    except IndexError:
        raise Exception('Unable to parse address %s' % addr)

    try:
        port  = int(m.group('port'))
    except IndexError:
        port = default_port

    return (host, port)

def http_send_request(socket, request):
    fp = socket.makefile()
    fp.write("%s %s %s\r\n" % (request.method, request.uri, request.version))
    for header in request.headers:
        fp.write("%s: %s\r\n" % (header, request.headers[header]))
    fp.write("\r\n")
    fp.write(request.body)
    fp.close()

def http_send_reply(socket, reply):
    fp = socket.makefile()
    fp.write("%s %d %s\r\n" % (reply.version, reply.code, reply.message))
    for header in reply.headers:
        fp.write("%s: %s\r\n" % (header, reply.headers[header]))
    fp.write("\r\n")
    fp.write(reply.body)
    fp.close()

def http_has_header(headers, header):
    return http_get_header(headers, header) != None

def http_match_header(headers, header, value):
    header = http_get_header(headers, header)
    if header:
        return header.lower() == value.lower()
    else:
        return False

def http_get_header(headers, header):
    header = header.lower()

    for (name, value) in headers.iteritems():
        if name.lower() == header:
            return value

    return None

def http_set_header(headers, header, value):
    header_low = header.lower()

    for name in headers:
        if name.lower() == header_low:
            headers[name] = value
            return 

    headers[header] = value

class HTTPRequest(object):
    def __init__(self, method = "GET", uri = "/", version = "HTTP/1.1", headers = None, body = ""):
        self.method = method
        self.version = version

        self.uri = uri
        self.args = {}
        if '?' in uri:
            (self.uri_path, self.uri_args) = self.uri.split('?', 1)

            if self.uri_args:
                items = self.uri_args.split('&')
                for item in items:
                    if '=' in item:
                        (arg, value) = item.split('=')
                        self.args[urllib.unquote_plus(arg)] = urllib.unquote_plus(value)
                    else:
                        self.args[item] = True

        else:
            self.uri_path = self.uri
            self.uri_args = ""

        self.uri_path = urllib.unquote(self.uri_path)

        if headers:
            self.headers = headers
        else:
            self.headers = {}

        self.body = body

        if not self.has_header('Content-Length'):
            self.set_header('Content-Length', len(self.body))

    def get_header(self, header):
        return http_get_header(self.headers, header)

    def set_header(self, header, data):
        http_set_header(self.headers, header, data)

    def has_header(self, header):
        return http_has_header(self.headers, header)

    def match_header(self, header, data):
        http_match_header(self.headers, header, data)

class HTTPReply(object):
    def __init__(self, version = 'HTTP/1.1', code = 200, message = None, headers = None, body = ''):
        self.version = version
        self.code = code
        self.message = message

        if headers:
            self.headers = headers
        else:
            self.headers = {}
        self.body = body

        if not self.message and self.code in ErrorCodes:
            self.message = ErrorCodes[self.code]

        if not self.has_header('Content-Length'):
            self.set_header('Content-Length', len(self.body))

    def get_header(self, header):
        return http_get_header(self.headers, header)

    def set_header(self, header, data):
        http_set_header(self.headers, header, data)

    def has_header(self, header):
        return http_has_header(self.headers, header)

    def match_header(self, header, data):
        http_match_header(self.headers, header, data)
