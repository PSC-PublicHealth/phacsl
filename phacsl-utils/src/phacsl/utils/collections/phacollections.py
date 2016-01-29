#! /usr/bin/env python

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

""" phacollections.py
This module contains specialized container/class types
"""



import collections
import types


def enum(*sequential, **named):
    """
    Thanks to stackoverflow user Alec Thomas for this answer to 'How can I represent an
    'Enum' in Python?'
    """
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['names'] = reverse
    return type('Enum', (), enums)


def namedtuple(typename, field_names, verbose=False, rename=False, field_types=None):
    """
    This is equivalent to collections.namedtuple(), but adds some support for printing
    enum strings and for pickling.
    """
    newTp = collections.namedtuple(typename, field_names, verbose=verbose, rename=rename)

    if field_types is not None:
        assert isinstance(field_types, types.ListType), "field_types is not a list"
        assert len(field_types) == len(field_names), \
            "field_types and field_names do not have matching lengths"

        def newrepr(self):
            'Return a nicely formatted representation string'
            bits = [typename, '(']
            start = True
            for fn, val, tp in zip(field_names, self, field_types):
                if tp is not None and tp.__name__ == 'Enum':
                    val = tp.names[val]
                else:
                    val = repr(val)
                if start:
                    start = False
                    bits.extend([fn, '=', val])
                else:
                    bits.extend([', ', fn, '=', val])
            bits.append(')')
            return ''.join(bits)

        newTp.__repr__ = newrepr

    assert newTp.__name__ not in globals(), \
        "module %s already has a type named %s" % (__name__, newTp.__name__)
    globals()[newTp.__name__] = newTp  # So the pickle can find it later

    return newTp


class SingletonMetaClass(type):
    """
    Thanks again to stackoverflow, this is a Singleton metaclass for Python.

    see http://stackoverflow.com/questions/6760685/creating-a-singleton-in-python

    Note that 'self' in this case should properly be 'cls' since it is a class, but
    the syntax checker doesn't like that.
    """
    _instances = {}

    def __call__(self, *args, **kwargs):  # stupid syntax checker does not understand metaclasses
        if self not in self._instances:
            self._instances[self] = super(SingletonMetaClass, self).__call__(*args, **kwargs)
        return self._instances[self]
