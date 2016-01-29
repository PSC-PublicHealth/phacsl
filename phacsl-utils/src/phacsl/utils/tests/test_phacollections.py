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
import unittest
from phacsl.utils.collections import enum, namedtuple, SingletonMetaClass

import types

class TestUtilFuncs(unittest.TestCase):
    def test_singletonmeta(self):
        class MyClass(object):
            __metaclass__ = SingletonMetaClass
            instanceCounter = 0

            def __init__(self):
                self.id = self.instanceCounter
                self.instanceCounter += 1

        inst1 = MyClass()
        inst2 = MyClass()
        self.assertTrue(inst1 is inst2, "Singleton is-ness failed")
        self.assertTrue(inst1.id == inst2.id, "Singleton ids do not match")

    def test_namedtuple1(self):
        CareTier = enum('HOME', 'HOSP')
        PatientStatus = namedtuple('PatientStatus', ['careTier', 'thing', 'age'],
                                   field_types=[CareTier, None, types.IntType])
        thing = PatientStatus(CareTier.HOSP, 'first', 7)
        self.assertTrue(str(thing) == "PatientStatus(careTier=HOSP, thing='first', age=7)",
                        "namedtuple.__str__ failed")
        self.assertTrue(repr(thing) == "PatientStatus(careTier=HOSP, thing='first', age=7)",
                        "namedtuple.__repr__ failed")

    def test_namedtuple2(self):
        import pickle
        CareTier = enum('HOME', 'HOSP')
        NewStatus = namedtuple('NewStatus', ['careTier', 'thing', 'age'],
                               field_types=[CareTier, None, types.IntType])
        thing = NewStatus(CareTier.HOSP, 'first', 7)
        pStr = pickle.dumps(thing)
        thing2 = pickle.loads(pStr)
        self.assertTrue((thing.careTier == thing2.careTier) and (thing.thing == thing2.thing)
                        and (thing.age == thing2.age),
                        "namedtuple pickling failed")
        self.assertTrue(str(thing2) == str(thing), "namedtuple pickling fails to preserve __str__")


if __name__ == '__main__':
    unittest.main()

