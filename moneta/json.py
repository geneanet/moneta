# -*- coding: utf-8 -*-



import json
import datetime
import dateutil.parser
import re

iso_datetime_regex = re.compile(r"^(\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\d\.\d+([+-][0-2]\d:[0-5]\d|Z)?)|(\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d:[0-5]\d([+-][0-2]\d:[0-5]\d|Z)?)|(\d{4}-[01]\d-[0-3]\dT[0-2]\d:[0-5]\d([+-][0-2]\d:[0-5]\d|Z)?)$")

def new_scanstring(s, end, strict=True):
    (s, end) = json.decoder.scanstring(s, end, strict)
    if iso_datetime_regex.match(s):
        return (dateutil.parser.parse(s), end)
    else:
        return (s, end)

class JSONDecoder(json.JSONDecoder):
    """ JSON Decoder that transforms ISO time format representations into datetime.datetime """
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, *args, **kwargs)
        self.parse_string = new_scanstring
        self.scan_once = json.scanner.py_make_scanner(self) # Use the python version as the C version do not use the new parse_string

def custom_encoder(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    else:
        raise TypeError

def dumps(obj, *args, **kwargs):
    kwargs['default'] = custom_encoder
    return json.dumps(obj, *args, **kwargs)

def loads(s, *args, **kwargs):
    kwargs['cls'] = JSONDecoder
    return json.loads(s, *args, **kwargs)