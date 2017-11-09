#! /usr/bin/env python
# -*- coding: utf8 -*-

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

import sys
import unittest
import types
import StringIO

import phacsl.utils.formats.kvp_tools as kvp_tools
from phacsl.utils.formats.kvp_tools import ParserException


def main():
    "This is a simple test routine which takes kvp files as arguments"

    parser = kvp_tools.KVPParser()
    parseThese = []
    for a in sys.argv[1:]:
        if a == '-v':
            parser.verbose = True
        elif a == '-d':
            parser.debug = True
        else:
            parseThese.append(a)

    if parser.debug:
        # Run some internal tests
        for rec in [a for a, b in TestKVPTools.samples]:  # @UnusedVariable
            try:
                d = parser.parse([rec], encoding='utf8')
                print(d)
            except ParserException, e:
                print(e)

    for thing in parseThese:
        print(("##### Checking %s" % thing))
        d = parser.parse(thing)
        if parser.verbose:
            parser.writeKVP(sys.stdout, d)
        with open('test_kvp_tools.kvp', 'w') as f:
            parser.writeKVP(f, d)
        with open('test_kvp_tools.kvp', 'rU') as f:
            testDict = parser.parse(f)
        assert(testDict == d)


class TestKVPTools(unittest.TestCase):
    samples = [("# This is a pure comment", {}),
               ("    # so is this   ", {}),
               ("foo", {'foo': True}),
               ("bar # my comment", {'bar': True}),
               ("thing=124", {'thing': 124}),
               ("thing2 =-123", {'thing2': -123}),
               ("thing3= +123", {'thing3': 123}),
               ('thing4 = "foo"', {'thing4': 'foo'}),
               ("lthing = 12,34;56:'foo' # a list", {'lthing': [12, 34, 56, 'foo']}),
               ("""other='hello',12,'and "more" stuff'\t# comment""",
                {'other': ['hello', 12, 'and "more" stuff']}),
               ("thing5=-17.2", {'thing5': -17.2}),
               ("thing6= 18.27", {'thing6': 18.27}),
               ("thing8=+19.3", {'thing8': 19.3}),
               ("thing9=+.8", {'thing9': 0.8}),
               ("thing10=.82", {'thing10': 0.82}),
               ("thing11=7.", {'thing11': 7.0}),
               ("thing12=+8.", {'thing12': 8.0}),
               ("lthing2= 0.8e3,7.e3,-4.2E-03", {'lthing2': [800.0, 7000.0, -0.0042]}),
               ("someidentifier,", "Failed to parse <someidentifier,>"),
               ("thing13='quoted string with an 0.8 embedded float'",
                {'thing13': 'quoted string with an 0.8 embedded float'}),
               ("somebool= True", {'somebool': True}),
               ("somebool= false", {'somebool': False}),
               ("something= None", {'something': None}),
               ('utf8sample= "Dépôt Central*"', {'utf8sample': u'Dépôt Central*'}),
               ]

    def test_kvptools(self):
        parser = kvp_tools.KVPParser()
        totalDict = {}
        for rec, expectedResult in TestKVPTools.samples:
            try:
                d = parser.parse([rec], encoding='utf8')
                self.assertTrue(isinstance(expectedResult, types.DictType))
                if d != expectedResult:
                    print(("error: got %s expected %s" % (d, expectedResult)))
                self.assertTrue(d == expectedResult)
                totalDict.update(d)
            except ParserException, e:
                self.assertTrue(isinstance(expectedResult, types.StringTypes))
                self.assertTrue(str(e) == expectedResult)
        outSIO = StringIO.StringIO()
        parser.writeKVP(outSIO, totalDict, encoding='utf8')
        inSIO = StringIO.StringIO(outSIO.getvalue())
        testDict = parser.parse(inSIO, encoding='utf8')
        self.assertTrue(testDict == totalDict)
        for k, v in testDict.items():
            # print "<%s>:<%s>"%(k,v)
            self.assertTrue(k in totalDict and totalDict[k] == v)

############
# Main hook
############

if __name__ == "__main__":
    main()
