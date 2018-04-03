# -*- coding: utf-8 -*-

class ExecutionDisabled(Exception):
    """ Exception thrown if the manager cannot execute task because execution is disabled """
    pass

class NotFound(Exception):
    """ Exception thrown if a requested object is not found in a collection """
    pass

class ProcessNotFound(NotFound):
    """ Exception thrown when a requested process is not found """
    pass
