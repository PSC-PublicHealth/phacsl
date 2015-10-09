#!/usr/bin/env python

###################################################################################
# Copyright   2015, Pittsburgh Supercomputing Center (PSC).  All Rights Reserved. #
# =============================================================================== #
#                                                                                 #
# Permission to use, copy, and modify this software and its documentation without #
# fee for personal use within your organization is hereby granted, provided that  #
# the above copyright notice is preserved in all copies and that the copyright    #
# and this permission notice appear in supporting documentation.  All other       #
# restrictions and obligations are defined in the GNU Affero General Public       #
# License v3 (AGPL-3.0) located at http://www.gnu.org/licenses/agpl-3.0.html  A   #
# copy of the license is also provided in the top level of the source directory,  #
# in the file LICENSE.txt.                                                        #
#                                                                                 #
###################################################################################

""" util.py
This module holds miscellaneous utility functions that do not have
a natural home elsewhere.
"""

import sys
import types
import locale
import codecs


def isiterable(c):
    "simple test for iterability"
    if hasattr(c, '__iter__') and callable(c.__iter__):
        return True
    return False


def listify(v, keepNone=False):
    """
    make something iterable if it isn't already
    """
    if keepNone:
        if v is None:
            return None
    if v is None:
        return []

    # I'm going to arbitrarily say that dicts aren't lists.  The question is if I should
    # just ask if v is a list or tuple and modify otherwise
    if isinstance(v, dict):
        return [v]

    if isiterable(v):
        return v
    return [v]


class logContext:
    context = []

    def __init__(self, msg):
        logContext.context.append(msg)

    def __enter__(self):
        return logContext.context

    def __exit__(self, b, c, d):
        logContext.context.pop()


def raiseRuntimeError(msg):
    print "****** Begin Fatal Error ******"
    for c in logContext.context:
        print c
    print msg
    print "****** End Fatal Error ********"
    raise RuntimeError(msg)


def logError(msg):
    print "****** Begin Non-Fatal Error ******"
    for c in logContext.context:
        print c
    print msg
    print "****** End Non-Fatal Error ********"


def logWarning(msg):
    print "****** Begin Warning ******"
    for c in logContext.context:
        print c
    print msg
    print "****** End Warning ********"


def _modify_for_nested_pickle(cls, name_prefix, module):
    for (name, v) in cls.__dict__.iteritems():
        if isinstance(v, (type, types.ClassType)):
            if (v.__name__ == name and v.__module__ == module.__name__
                    and getattr(module, name, None) is not v):
                # OK, probably this is a nested class.
                dotted_name = name_prefix + '.' + name
                v.__name__ = dotted_name
                setattr(module, dotted_name, v)
                _modify_for_nested_pickle(v, dotted_name, module)


def nested_pickle(cls):
    """
    Taken from http://trac.sagemath.org/sage_trac/browser/sage/misc/nested_class.py
    calling nested_pickle() on an class with subclasses should help pickle handle
    the subclasses.
    """
    _modify_for_nested_pickle(cls, cls.__name__, sys.modules[cls.__module__])
    return cls


class strongRef:
    """
    Use as a replacement for a weakref when pickling
    """
    def __init__(self, ref):
        self.ref = ref()

    def __call__(self):
        return self.ref


def getPreferredOutputEncoding(baseEncoding=None):
    if baseEncoding is None:
        outEncoding = locale.getpreferredencoding()
    else:
        outEncoding = baseEncoding
    outEncoding = outEncoding.lower().replace('-', '')
    encodingMap = {'cp65001': 'cp1252',  # Windows PowerShell
                   'windows1252': 'cp1252',
                   }
    if outEncoding in encodingMap:
        outEncoding = encodingMap[outEncoding]
    try:
        codecs.lookup(outEncoding)
    except:
        outEncoding = 'utf8'
    return outEncoding


class openByNameOrFile():
    """
    usable when you have either a filename or a filehandle and don't want to know which.
    Only use this in the context handler case (ie "with openFileOrHandle() as f:")
    """
    def __init__(self, ifile, mode='rU'):
        self.handle = None
        self.odfHandle = None
        if not isinstance(ifile, types.StringTypes):
            self.handle = ifile
        else:
            self.odfHandle = open(ifile, mode)
            self.handle = self.odfHandle

    def __enter__(self):
        return self.handle

    def __exit__(self, typ, value, traceback):
        if self.odfHandle is not None:
            self.odfHandle.close()
