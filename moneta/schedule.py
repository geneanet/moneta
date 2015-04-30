# -*- coding: utf-8 -*-

from __future__ import absolute_import

import datetime
import re

class Schedule(object):
    """ Class representing a cron schedule """

    def __init__(self, month = None, week = None, dayofweek = None, dayofmonth = None, hour = None, minute = None):
        self.month = self.__expand(month, 0, 12)
        self.week = self.__expand(week, 0, 52)
        self.dayofweek = self.__expand(dayofweek, 0, 7)
        self.dayofmonth = self.__expand(dayofmonth, 0, 31)
        self.hour = self.__expand(hour, 0, 23)
        self.minute = self.__expand(minute, 0, 59)

    def match_interval(self, beginning, end, include_beginning = True, include_end = False):
        """ Check if the task is scheduled at least one time in the interval """

        if include_beginning:
            current = beginning
        else:
            current = current + datetime.timedelta(microseconds = 1)

        # Round to next second
        if current.microsecond > 0:
            current = current + datetime.timedelta(microseconds = 1000000 - current.microsecond)

        # Round to next minute
        if current.second > 0:
            current = current + datetime.timedelta(seconds = 60 - current.second)

        while current < end or (include_end and current == end):
            if self.match(current):
                return True

            current = current + datetime.timedelta(minutes = 1)

    def match(self, t):
        """ Check if a datetime matches the schedule """

        month = t.month
        (year, week, dayofweek) = t.isocalendar()
        dayofmonth = t.day
        hour = t.hour
        minute = t.minute

        return self.__match_value(month, self.month) and self.__match_value(week, self.week) and self.__match_value(dayofweek, self.dayofweek) and self.__match_value(dayofmonth, self.dayofmonth) and self.__match_value(hour, self.hour) and self.__match_value(minute, self.minute)

    @staticmethod
    def __match_value(needle, haystack):
        """ Check if needle is equals to haystack, or included in haystack (if haystack is a list) or if haystack is None, empty list, empty string or wildcard """

        if haystack in [ None, [], "", "*" ]:
            return True

        if isinstance(haystack, list):
            return needle in haystack
        else:
            return needle == haystack

    @staticmethod
    def __expand(data, minimum, maximum):
        """ Expands */x into a list from 0 to maximum with steps of x. Recursive. """

        if isinstance(data, list):
            out = []

            for item  in data:
                expanded = Schedule.__expand(item, minimum, maximum)
                if isinstance(expanded, list):
                    out.extend(expanded)
                else:
                    out.append(expanded)

            out = list(set(out))

            if out == []:
                return None
            else:
                return list(set(out))

        elif isinstance(data, str) or isinstance(data, unicode):
            if data == '':
                return None

            int_re = re.match(r'^[0-9]+$', data)
            list_re = re.match(r'^[0-9\-*/]+(,[0-9\-*/]+)+$', data)
            range_re = re.match(r'^(?P<min>[0-9]+)-(?P<max>[0-9]+)$', data)
            wildcard_re = re.match(r'^\*(?:/(?P<step>[0-9]+))?$', data)

            if int_re:
                return int(data)

            elif list_re:
                return Schedule.__expand(data.split(','), minimum, maximum)

            elif range_re:
                return range(int(range_re.group('min')), int(range_re.group('max')) + 1)

            elif wildcard_re:
                if wildcard_re.group('step'):
                    step = int(wildcard_re.group('step'))
                else:
                    step = 1

                return range(minimum, maximum + 1, step)

            else:
                raise Exception('Unable to parse schedule: %s', data)

        else:
            return data

    def __repr__(self):
        return "Schedule(month = %s, week = %s, dayofweek = %s, dayofmonth = %s, hour = %s, minute = %s)" % (repr(self.month), repr(self.week), repr(self.dayofweek), repr(self.dayofmonth), repr(self.hour), repr(self.minute))
