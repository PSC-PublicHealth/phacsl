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
import cStringIO
import cPickle
import unittest

from phacsl.utils.notes.statval import StatVal, AccumVal, TimeStampAccumVal, HistoVal, AccumMultiVal
from phacsl.utils.notes.statval import TagAwareDict


def describeSelf():
    print \
        """
        Testing options:

          teststat

             does simple tests of StatVal

          testaccum

             does simple tests of AccumVal

          testtimestampaccum

             does simple tests of TimeStampAccumVal

          testhisto

             does simple tests of HistoVal

          testtagawaredict

             Run some tests on the TagAwareDict class
        """

_testrandseq = [0.57417, 0.33765, 0.58059, 0.67528, 0.61572, 0.74997, 0.83605, 0.70498, 0.26290,
                0.88133, 0.00186, 0.58914, 0.66510, 0.62194, 0.09087, 0.37141, 0.79331, 0.21574,
                0.92974, 0.91812, 0.13869, 0.09136, 0.59309, 0.43779, 0.99285, 0.42980, 0.66230,
                0.36791, 0.13671, 0.54168, 0.22997, 0.02101, 0.79965, 0.77871, 0.75635, 0.02062,
                0.36131, 0.17745, 0.48464, 0.68112, 0.60856, 0.88117, 0.48980, 0.64864, 0.44530,
                0.82017, 0.75527, 0.91085, 0.69330, 0.93517]
_testrandindex = 0


def _testrandreset():
    global _testrandindex
    _testrandindex = 0


def _testrand():
    """
    For testing purposes, a sequence of 'random' numbers.  The Python 'random' module seems to have
    inconsistencies across versions which lead to problems.
    """
    global _testrandindex
    v = _testrandseq[_testrandindex]
    _testrandindex = (_testrandindex + 1) % len(_testrandseq)
    return v


def main(myargv=None):
    "Provides a few test routines"
    import random

    if myargv is None:
        myargv = sys.argv

    if len(myargv) < 2:
        describeSelf()

    elif myargv[1] == 'teststat':
        if len(myargv) == 2:
            s = StatVal(0.0)
            print s
            print repr(s)
            for v in [0.37338394029779121, 0.90957338184897241, 0.15996060530020217,
                      0.83193287665351767, 0.05340812724513877, 0.38946846756156384,
                      0.63321268843855927, 0.64064429019556424, 0.29513138953437823,
                      0.83588832473090924]:
                s2 = StatVal(v)
                s += s2
            print s
            print repr(s)
        else:
            print "Wrong number of arguments!"
            describeSelf()

    elif myargv[1] == 'testaccum':
        if len(myargv) == 2:
            randState = random.getstate()
            random.seed(1234)
            _testrandreset()
            s = AccumVal(0.0)
            print s
            print repr(s)
            for i in xrange(5):
                s2 = AccumVal(_testrand())
                s += s2
            print repr(s)
            for i in xrange(5):
                s += _testrand()
            print repr(s)
            s2 = AccumVal(_testrand())
            for i in xrange(5):
                s2 += _testrand()
            s += s2
            print repr(s2)
            print repr(s)
            s += s
            print "Histogram = " + repr(s.histogram())
            s = AccumVal(random.gauss(0.5, 0.3))
            for i in xrange(1000):
                s += random.gauss(0.5, 0.3)
            print "%d samples supposedly Gaussian(0.5, 0.3):" % s.count()
            print "mean: %7g" % s.mean()
            print "stdv: %7g" % s.stdv()
            print "min: %7g" % s.min()
            print "max: %7g" % s.max()
            print "median: %7g" % s.median()
            random.setstate(randState)
        else:
            print "Wrong number of arguments!"
            describeSelf()

    elif myargv[1] == 'testtimestampaccum':
        if len(myargv) == 2:
            _testrandreset()
            s = TimeStampAccumVal(0.0, (1.0, 4.0))
            print s.t
            print repr(s)
            for i in range(1, 5):
                s2 = TimeStampAccumVal(_testrand(), (i, i+1))
                s += s2
            print repr(s)
            for i in range(5, 10):
                s += (_testrand(), i)
            print repr(s)
        else:
            print "Wrong number of arguments!"
            describeSelf()

    elif myargv[1] == 'testhisto':
        if len(myargv) == 2:
            randState = random.getstate()
            random.seed(1234)
            _testrandreset()
            s = HistoVal([random.gauss(0.5, 0.3), random.gauss(0.5, 0.3)], quantum=0.2)
            print repr(s)
            for i in xrange(100):
                s += random.gauss(0.5, 0.3)
            print "%d samples supposedly Gaussian(0.5, 0.3):" % s.count()
            print "mean: %7g" % s.mean()
            print "stdv: %7g" % s.stdv()
            print "min: %7g" % s.min()
            print "max: %7g" % s.max()
            print "median: %7g" % s.median()
            print "q1: %7g" % s.q1()
            print "q3: %7g" % s.q3()
            print "textstr: %s" % s.textStr()
            hL = [(v, n) for v, n in s.histogram().items()]
            hL.sort()
            print "histogram: { %s }" % ', '.join(["%5f: %d" % (v, n) for v, n in hL])
            s1 = HistoVal([0.0, 0.01, 0.0], quantum=0.1)
            hL = [(v, n) for v, n in s1.histogram().items()]
            hL.sort()
            print "adding histoval with histogram { %s }" % ', '.join(["%5f: %d" % (v, n)
                                                                       for v, n in hL])
            s += s1
            hL = [(v, n) for v, n in s.histogram().items()]
            hL.sort()
            print "yields { %s }" % ', '.join(["%5f: %d" % (v, n) for v, n in hL])
            print 'compare two inequal vals: %s' % (s == s1)
            random.setstate(randState)
            try:
                fakeF = cStringIO.StringIO()
                cPickle.dump(s, fakeF)
                newS = cPickle.loads(fakeF.getvalue())
                print 'pickling and unpickling worked: %s' % newS
            except Exception, e:
                print 'pickling or unpickling failed: %s' % str(e)
            try:
                newS = HistoVal.fromJSON(s.toJSON())
                print newS.d
                print 'toJSON and fromJSON worked: %s' % newS
                print 'compare two equal vals: %s' % (s == newS)
            except Exception, e:
                print 'toJSON and fromJSON failed: %s' % str(e)
        else:
            print "Wrong number of arguments!"
            describeSelf()

    elif myargv[1] == 'testaccummultival':
        if len(myargv) == 2:
            names = ["foo", "bar", "baz", "qux"]
            values = [(1, 2, 3, 4), (5, 6, 7, 8), (9, 10, 11, 12), (13, 14, 15, 16)]

            amv = AccumMultiVal(names, values[0])
            for v in values[1:]:
                amv.v.append(v)
            compString = amv.packWKeys()

            newAMV = amv.fromPackedStringWHeaders(compString)

            print str(newAMV)
            print repr(newAMV)
        else:
            describeSelf()

    elif myargv[1] == 'testtagawaredict':
        if len(myargv) == 2:
            d = TagAwareDict(AccumVal, [('_ave', AccumVal.mean),
                                        ('_stdv', AccumVal.stdv),
                                        ('_min', AccumVal.min),
                                        ('_max', AccumVal.max),
                                        ('_median', AccumVal.median),
                                        ('_count', AccumVal.count)],
                             innerDict={'baz': 37.2})
            d["foo"] = 7
            d["bar"] = AccumVal(9)
            d["bar"] += 12
            d["bar"] += 13
            d["bar"] += 8
            d["bar"] += 8

            print "repr: " + repr(d["bar"])
            print "str: " + str(d["bar"])
            print ("ave, stdv, min, max, median, count: %s"
                   % [d["bar"+s] for s in ['_ave', '_stdv', '_min', '_max', '_median', '_count']])
            print "length should be 7: %d" % len(d)
            print ("testing 'in' for ['foo','bar_ave','bar_stdv','bar_min','bar_max','bar_median',"
                   "'bar_count','bar_zz']: %s" %
                   [k in d for k in ['foo', 'bar_ave', 'bar_stdv', 'bar_min', 'bar_max',
                                     'bar_median', 'bar_count', 'bar_zz']])
            print ("testing 'in' for ['foo_ave','foo_stdv','foo_min','foo_max',"
                   "'foo_median','foo_count']: %s" %
                   [k in d for k in ['foo_ave', 'foo_stdv', 'foo_min',
                                     'foo_max', 'foo_median', 'foo_count']])
            print ("testing 'in' for ['blrfl','blrfl_ave','blrfl_stdv','blrfl_min',"
                   "'blrfl_max','blrfl_median','blrfl_count']: %s" %
                   [k in d for k in ['blrfl', 'blrfl_ave', 'blrfl_stdv', 'blrfl_min', 'blrfl_max',
                                     'blrfl_median', 'blrfl_count']])

            i = iter(d)
            try:
                while True:
                    print 'next yields ' + i.next()
            except StopIteration:
                print "StopIteration happened"
            print "items: %s" % d.items()
            for k in d.keys():
                del d[k]
            print "items after deletes: %s" % d.items()

        else:
            describeSelf()

    else:
        describeSelf()


class TestUtilFuncs(unittest.TestCase):
    def getReadBackBuf(self, wordList):
        try:
            sys.stdout = myStdout = cStringIO.StringIO()
            main(wordList)
        finally:
            sys.stdout = sys.__stdout__
        return cStringIO.StringIO(myStdout.getvalue())

    def test_tagawaredict(self):
        correctStr = """repr: AccumVal([9.0, 12.0, 13.0, 8.0, 8.0])
str: 10.0+-2.3452078799117149
ave, stdv, min, max, median, count: [10.0, 2.3452078799117149, 8.0, 13.0, 9.0, 5]
length should be 7: 8
testing 'in' for ['foo','bar_ave','bar_stdv','bar_min','bar_max','bar_median','bar_count','bar_zz']: [True, True, True, True, True, True, True, False]
testing 'in' for ['foo_ave','foo_stdv','foo_min','foo_max','foo_median','foo_count']: [False, False, False, False, False, False]
testing 'in' for ['blrfl','blrfl_ave','blrfl_stdv','blrfl_min','blrfl_max','blrfl_median','blrfl_count']: [False, False, False, False, False, False, False]
next yields bar_ave
next yields bar_stdv
next yields bar_min
next yields bar_max
next yields bar_median
next yields bar_count
next yields foo
next yields baz
StopIteration happened
items: [('bar_ave', 10.0), ('bar_stdv', 2.3452078799117149), ('bar_min', 8.0), ('bar_max', 13.0), ('bar_median', 9.0), ('bar_count', 5), ('foo', 7), ('baz', 37.200000000000003)]
items after deletes: []
        """
        readBack = self.getReadBackBuf(['dummy', 'testtagawaredict'])
        correctRecs = cStringIO.StringIO(correctStr)
        for a, b in zip(readBack.readlines(), correctRecs.readlines()):
            self.assertTrue(a.strip() == b.strip())

    def test_statval(self):
        correctStr = """StatVal(0.0)
StatVal(0.0,1,0.0,0.0)
StatVal(0.90957338184897241)
StatVal(5.12260409181,11,0.0,0.909573381849)
        """
        readBack = self.getReadBackBuf(['dummy', 'teststat'])
        correctRecs = cStringIO.StringIO(correctStr)
        for a, b in zip(readBack.readlines(), correctRecs.readlines()):
            if a.strip() != b.strip():
                print "\nExpected: <%s>" % b.strip()
                print "Got     : <%s>" % a.strip()
            self.assertTrue(a.strip() == b.strip())

    def test_tagawaredict2(self):
        correctStr = """repr: AccumVal([9.0, 12.0, 13.0, 8.0, 8.0])
str: 10.0+-2.3452078799117149
ave, stdv, min, max, median, count: [10.0, 2.3452078799117149, 8.0, 13.0, 9.0, 5]
length should be 7: 8
testing 'in' for ['foo','bar_ave','bar_stdv','bar_min','bar_max','bar_median','bar_count','bar_zz']: [True, True, True, True, True, True, True, False]
testing 'in' for ['foo_ave','foo_stdv','foo_min','foo_max','foo_median','foo_count']: [False, False, False, False, False, False]
testing 'in' for ['blrfl','blrfl_ave','blrfl_stdv','blrfl_min','blrfl_max','blrfl_median','blrfl_count']: [False, False, False, False, False, False, False]
next yields bar_ave
next yields bar_stdv
next yields bar_min
next yields bar_max
next yields bar_median
next yields bar_count
next yields foo
next yields baz
StopIteration happened
items: [('bar_ave', 10.0), ('bar_stdv', 2.3452078799117149), ('bar_min', 8.0), ('bar_max', 13.0), ('bar_median', 9.0), ('bar_count', 5), ('foo', 7), ('baz', 37.200000000000003)]
items after deletes: []
        """
        readBack = self.getReadBackBuf(['dummy', 'testtagawaredict'])
        correctRecs = cStringIO.StringIO(correctStr)
        for a, b in zip(readBack.readlines(), correctRecs.readlines()):
            if a.strip() != b.strip():
                print "\nExpected: <%s>" % b.strip()
                print "Got     : <%s>" % a.strip()
            self.assertTrue(a.strip() == b.strip())

    def test_accum(self):
        correctStr = """0.0+-0.0
AccumVal([0.0])
AccumVal([0.0, 0.57417, 0.33765, 0.58059, 0.67528, 0.61572])
AccumVal([0.0, 0.57417, 0.33765, 0.58059, 0.67528, 0.61572, 0.74997, 0.83605, 0.70498, 0.2629, 0.88133])
AccumVal([0.00186, 0.58914, 0.6651, 0.62194, 0.09087, 0.37141])
AccumVal([0.0, 0.57417, 0.33765, 0.58059, 0.67528, 0.61572, 0.74997, 0.83605, 0.70498, 0.2629, 0.88133, 0.00186, 0.58914, 0.6651, 0.62194, 0.09087, 0.37141])
Histogram = {0.0: 2, 0.6651: 2, 0.88133: 2, 0.58914: 2, 0.00186: 2, 0.58059: 2, 0.57417: 2, 0.83605: 2, 0.67528: 2, 0.2629: 2, 0.61572: 2, 0.09087: 2, 0.74997: 2, 0.33765: 2, 0.62194: 2, 0.37141: 2, 0.70498: 2}
1001 samples supposedly Gaussian(0.5, 0.3):
mean: 0.512872
stdv: 0.300405
min: -0.37918
max:  1.3922
median: 0.505264
        """
        readBack = self.getReadBackBuf(['dummy', 'testaccum'])
        correctRecs = cStringIO.StringIO(correctStr)
        for a, b in zip(readBack.readlines(), correctRecs.readlines()):
            self.assertTrue(a.strip() == b.strip())

    def test_timestampaccum(self):
        correctStr = """[(1.0, 4.0)]
TimeStampAccumVal(v:[0.0],t:[(1.0, 4.0)])
TimeStampAccumVal(v:[0.0, 0.57417, 0.33765, 0.58059, 0.67528],t:[(1.0, 4.0), (1.0, 2.0), (2.0, 3.0), (3.0, 4.0), (4.0, 5.0)])
TimeStampAccumVal(v:[0.0, 0.57417, 0.33765, 0.58059, 0.67528, 0.61572, 0.74997, 0.83605, 0.70498, 0.2629],t:[(1.0, 4.0), (1.0, 2.0), (2.0, 3.0), (3.0, 4.0), (4.0, 5.0), 5.0, 6.0, 7.0, 8.0, 9.0])
        """
        readBack = self.getReadBackBuf(['dummy', 'testtimestampaccum'])
        correctRecs = cStringIO.StringIO(correctStr)
        for a, b in zip(readBack.readlines(), correctRecs.readlines()):
            self.assertTrue(a.strip() == b.strip())

############
# Main hook
############

if __name__ == "__main__":
    main()
