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


# from https://stackoverflow.com/questions/6229073/how-to-make-a-python-dictionary-that-returns-key-for-keys-missing-from-the-dicti
def DefaultDict(keygen):
    '''
    Sane **default dictionary** (i.e., dictionary implicitly mapping a missing
    key to the value returned by a caller-defined callable passed both this
    dictionary and that key).

    The standard :class:`collections.defaultdict` class is sadly insane,
    requiring the caller-defined callable accept *no* arguments. This
    non-standard alternative requires this callable accept two arguments:

    #. The current instance of this dictionary.
    #. The current missing key to generate a default value for.

    Parameters
    ----------
    keygen : CallableTypes
        Callable (e.g., function, lambda, method) called to generate the default
        value for a "missing" (i.e., undefined) key on the first attempt to
        access that key, passed first this dictionary and then this key and
        returning this value. This callable should have a signature resembling:
        ``def keygen(self: DefaultDict, missing_key: object) -> object``.
        Equivalently, this callable should have the exact same signature as that
        of the optional :meth:`dict.__missing__` method.

    Returns
    ----------
    MappingType
        Empty default dictionary creating missing keys via this callable.
    '''

    # Global variable modified below.
    global _DEFAULT_DICT_ID

    # Unique classname suffixed by this identifier.
    default_dict_class_name = 'DefaultDict' + str(_DEFAULT_DICT_ID)

    # Increment this identifier to preserve uniqueness.
    _DEFAULT_DICT_ID += 1

    # Dynamically generated default dictionary class specific to this callable.
    default_dict_class = type(
        default_dict_class_name, (dict,), {'__missing__': keygen,})

    # Instantiate and return the first and only instance of this class.
    return default_dict_class()


_DEFAULT_DICT_ID = 0
'''
Unique arbitrary identifier with which to uniquify the classname of the next
:func:`DefaultDict`-derived type.
'''
