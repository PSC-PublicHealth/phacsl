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

"""statval.py
This module provides classes implementing statistical types.  They are typically
used in the context of NoteHolder instances.
"""

import sys
import math
import types
import unittest
import cStringIO
import cPickle
import json
from collections import MutableMapping
import struct
import string

from ..misc import util

nested_pickle = util.nested_pickle
isiterable = util.isiterable
listify = util.listify


def _castToFloatHighWater(v):
    if v is None or v == 'NA':
        return True, 0.0
    elif type(v) == StatVal:
        return True, v.max()
    elif type(v) == HistoVal:
        return True, v.max()
    else:
        try:
            return True, float(v)
        except:
            return False, None


def _castToIntHighWater(v):
    if v is None or v == 'NA':
        return True, 0
    elif type(v) == StatVal:
        return False, None  # it's probably an error to see a StatVal in this context
    elif type(v) == HistoVal:
        return False, None  # it's probably an error to see a HistoVal in this context
    else:
        try:
            return True, int(v)
        except:
            return False, None


def maxStatVal(sv):
    return sv.max()


def textStrStatVal(sv):
    return "StatVal(%r)" % sv.maxval


def meanStatVal(sv):
    return sv.mean()


class StatVal:
    def __init__(self, v, defaultFn=maxStatVal, defaultStr=textStrStatVal):
        self.v = v
        self.count = 1
        self.minval = v
        self.maxval = v
        self.defaultFn = defaultFn
        self.defaultStr = defaultStr

    def setDefaultFn(self, defaultFn=maxStatVal):
        self.defaultFn = defaultFn

    def setDefaultStr(self, defaultStr=textStrStatVal):
        self.defaultStr = defaultStr

    def __iadd__(self, other):
        self.v += other.v
        self.count += other.count
        if self.minval > other.minval:
            self.minval = other.minval
        if self.maxval < other.maxval:
            self.maxval = other.maxval
        return self

    def mean(self):
        return float(self.v)/self.count

    def min(self):
        return self.minval

    def max(self):
        return self.maxval

    def __float__(self):
        if isiterable(self.defaultFn):
            return self.defaultFn[0](self)
        return self.defaultFn(self)

    def __str__(self):
        if isiterable(self.defaultStr):
            ret = self.defaultStr[0](self)
        else:
            ret = self.defaultStr(self)
        return str(ret)

    def __repr__(self):
        return "StatVal(%s,%s,%s,%s)" % (self.v, self.count, self.minval, self.maxval)

# BUG Make AccumVal pickle well.  Either do away with function pointers or
# find a way of serializing/deserializing the pointers.


def maxAccumVal(av):
    return max(av.v)


def textStrAccumVal(av):
    return "%r+-%r" % (av.mean(), av.stdv())


def meanAccumVal(av):
    # count cannot be 0 because the constructor takes a val
    if av.meanV is None:
        av.meanV = sum(av.v)/len(av.v)
    return av.meanV


class AccumVal:
    # put max first so I can refer to it later.
    # ARRRRGGGGHHH!!!
    # can't pickle a function

    def textStr(self):
        return "%r+-%r" % (self.mean(), self.stdv())

    def __init__(self, v, defaultFn=maxAccumVal, defaultStr=textStrAccumVal):
        self.v = [float(v)]
        self.meanV = None
        self.stdvV = None
        self.defaultFn = defaultFn
        self.defaultStr = defaultStr
        self._sorted = False

    def setDefaultFn(self, defaultFn=maxAccumVal):
        self.defaultFn = defaultFn

    def setDefaultStr(self, defaultStr=textStrAccumVal):
        self.defaultStr = defaultStr

    def __iadd__(self, other):
        if isinstance(other, AccumVal):
            self.v += other.v
        elif type(other) in [types.IntType, types.FloatType, types.LongType]:
            self.v.append(float(other))
        else:
            raise RuntimeError("Tried to add %s to an AccumType" % repr(other))
        self.meanV = None
        self.stdvV = None
        self._sorted = False
        return self

    def _sort(self):
        self.v.sort()
        self._sorted = True

    def mean(self):
        # count cannot be 0 because the constructor takes a val
        if self.meanV is None:
            self.meanV = sum(self.v) / len(self.v)
        return self.meanV

    def stdv(self):
        self.mean()  # force the calculation
        if self.stdvV is None:
            if len(self.v) > 1:
                self.stdvV = math.sqrt(sum([(c - self.meanV) * (c-self.meanV)
                                            for c in self.v])
                                       / (len(self.v) - 1))
            else:
                self.stdvV = 0.0
        return self.stdvV

    def histogram(self):
        histDict = {}
        for vals in self.v:
            if vals in histDict:
                histDict[vals] += 1
            else:
                histDict[vals] = 1
        return histDict

    def min(self):
        if not self._sorted:
            self._sort()  # since we are probably sorting anyway
        return self.v[0]

    def max(self):
        if not self._sorted:
            self._sort()  # since we are probably sorting anyway
        return self.v[-1]

    def count(self):
        return len(self.v)

    def median(self):
        if not self._sorted:
            self._sort()
        return self.v[len(self.v)/2]

    def q1(self):
        if not self._sorted:
            self._sort()
        return self.v[len(self.v) / 4]

    def q3(self):
        if not self._sorted:
            self._sort()
        return self.v[(3*len(self.v)) / 4]

    def __float__(self):
        if isiterable(self.defaultFn):
            return self.defaultFn[0](self)
        return self.defaultFn(self)

    def __str__(self):
        if isiterable(self.defaultStr):
            ret = self.defaultStr[0](self)
        else:
            ret = self.defaultStr(self)
        return str(ret)
        # return "%r+-%r"%(self.mean(),self.stdv())

    def __repr__(self):
        return "AccumVal(%s)" % self.v

nested_pickle(AccumVal)


def maxHistoVal(av):
    return av.max()


def textStrHistoVal(av):
    return "%r+-%r" % (av.mean(), av.stdv())


def meanHistoVal(av):
    return av.mean()


class HistoVal(object):
    def textStr(self):
        return "%7g+-%7g" % (self.mean(), self.stdv())

    @staticmethod
    def _prep(item):
        if isinstance(item, types.TupleType):
            assert len(item) == 2 and isinstance(item[1], types.IntType), \
                "added invalid tuple %s to HistoVal" % (item)
            return (float(item[0]), item[1])
        else:
            return (float(item), 1)

    def _quantize(self, pairList):
        invQ = 1.0/self.d['quantum']
        for v, n in pairList:
            if v == 0.0:
                self.d['strictly_zero'] += n
            qV = int(math.floor(invQ*v))
            if qV in self.d:
                self.d[qV] += n
            else:
                self.d[qV] = n

    def _unquantize(self):
        q = self.d['quantum']
        hQ = 0.5*q
        for k, n in self.d.items():
            if isinstance(k, types.IntType):
                if k == 0:
                    yield (0.0, self.d['strictly_zero'])
                    yield (hQ, n - self.d['strictly_zero'])
                else:
                    yield ((k*q + hQ), n)

    def __init__(self, v, quantum=None, defaultFn=maxHistoVal, defaultStr=textStrHistoVal):
        if quantum is None:
            quantum = 0.5  # half a day
        elif quantum == 0.0:
            raise RuntimeError("HistoVal quantum cannot be zero")
        self.d = {'quantum': quantum, 'strictly_zero': 0}
        if isinstance(v, types.ListType):
            self._quantize([self._prep(x) for x in v])
        else:
            self._quantize([self._prep(v)])
        self.meanV = None
        self.stdvV = None
        self.countV = None
        self.defaultFn = defaultFn
        self.defaultStr = defaultStr
        self.v = None

    def setDefaultFn(self, defaultFn=maxHistoVal):
        self.defaultFn = defaultFn

    def setDefaultStr(self, defaultStr=textStrHistoVal):
        self.defaultStr = defaultStr

    def __iadd__(self, other):
        if isinstance(other, HistoVal):
            self._quantize(other._unquantize())
        else:
            self._quantize([self._prep(other)])
        self.meanV = None
        self.stdvV = None
        self.countV = None
        self.v = None
        return self

    def _sort(self):
        self.v = [(v, n) for v, n in self._unquantize()]
        self.v.sort()

    def count(self):
        if self.v is None:
            self._sort()
        if self.countV is None:
            self.countV = sum([b for a, b in self.v])  # @UnusedVariable
        return self.countV

    def mean(self):
        if self.v is None:
            self._sort()
        if self.v == []:
            return float('NaN')
        else:
            if self.meanV is None:
                self.meanV = sum([a*b for a, b in self.v])/self.count()
            return self.meanV

    def stdv(self):
        if self.v is None:
            self._sort()
        if self.stdvV is None:
            c = self.count()
            m = self.mean()
            if c > 1:
                self.stdvV = math.sqrt(sum([b * (a - m)*(a - m)
                                            for a, b in self.v])
                                       / (c - 1))
            else:
                self.stdvV = 0.0
        return self.stdvV

    def histogram(self):
        result = {}
        for v, n in self._unquantize():
            result[v] = n
        return result

    def raw(self):
        for a, b in self.histogram().items():
            for ignoreme in range(b):  # @UnusedVariable
                yield a

    def min(self):
        if self.v is None:
            self._sort()
        if self.v == []:
            return float('Nan')
        else:
            return self.v[0][0]

    def max(self):
        if self.v is None:
            self._sort()
        if self.v == []:
            return float('Nan')
        else:
            return self.v[-1][0]

    def median(self, _lim=None):
        if self.v is None:
            self._sort()
        if self.v == []:
            return float('NaN')
        else:
            if _lim is None:
                lim = self.count() / 2
            else:
                lim = _lim
            if lim is None:
                return float('NaN')  # This histo has no entries
            offset = 0
            for a, b in self.v:
                if offset + b >= lim:
                    return a
                offset += b
            raise RuntimeError('histo q1/median/q3 failed')

    def q1(self):
        return self.median(_lim=self.count()/4)

    def q3(self):
        return self.median(_lim=(3*self.count())/4)

    def __float__(self):
        if isiterable(self.defaultFn):
            return self.defaultFn[0](self)
        return self.defaultFn(self)

    def __str__(self):
        return "HistoVal(...%d...)" % self.count()

    def __repr__(self):
        return "HistoVal(%s)" % self.count()

    def toJSON(self):
        """
        The JSON string produced is the JSON representation of self.d
        """
        return json.dumps(self.d)

    @classmethod
    def fromJSON(cls, jsonString):
        d = json.loads(jsonString)
        # The JSON decoder turns our integer indices into strings- we need to fix that
        fixedD = {}
        for v, n in d.items():
            if v in ['quantum', 'strictly_zero']:
                fixedD[v] = n
            else:
                fixedD[int(v)] = n
        result = HistoVal([])
        result.d = fixedD
        return result

    def __cmp__(self, other):
        return self.d.__cmp__(other.d)

nested_pickle(HistoVal)


def maxTimeStampAccumVal(av):
    return max(av.v)


def textStrTimeStampAccumVal(av):
    return "%r,%r: %r-%r" % (av.minT(), av.maxT(), av.mean(), av.stdv())


class TimeStampAccumVal:
    def max(self):
        return max(self.v)

    def maxT(self):
        return max(self.t)

    def textStr(self):
        return "%r,%r: %r-%r" % (self.minT(), self.maxT(), self.mean(), self.stdv())

    def __init__(self, v, t, defaultFn=maxTimeStampAccumVal, defaultStr=textStrTimeStampAccumVal):
        self.v = [float(v)]
        if isinstance(t, tuple):
            self.t = [(float(t[0]), (float(t[1])))]
        else:
            self.t = [float(t)]
        self.defaultFn = defaultFn
        self.defaultStr = defaultStr

    def __iadd__(self, other):
        if isinstance(other, TimeStampAccumVal):
            self.v += other.v
            self.t += other.t
        elif len(other) == 2:
            if type(other[0]) in [types.IntType, types.FloatType, types.LongType]:
                if type(other[1]) in [types.IntType, types.FloatType, types.LongType]:
                    self.v.append(float(other[0]))
                    self.t.append(float(other[1]))
                else:
                    raise RuntimeError("Tried to add %s to a TimeStampAccumVal" % repr(other))
            else:
                raise RuntimeError("Tried to add %s to a TimeStampAccumVal" % repr(other))
        else:
            raise RuntimeError("Tried to add %s to a TimeStampAccumVal" % repr(other))

        return self

    def min(self):
        return min(self.v)

    def minT(self):
        return min(self.t)

    def mean(self):
        return sum(self.v)/len(self.v)

    def stdv(self):
        sum(self.v) / len(self.v)  # force calculation
        if len(self.v) > 1:
            return math.sqrt(sum([(c - self.mean()) * (c - self.mean())
                                  for c in self.v])
                             / (len(self.v) - 1))
        else:
            return 0.0

    def count(self):
        return len(self.v)

    def __float__(self):
        return float(0.0)

    def __str__(self):
        if isiterable(self.defaultStr):
            ret = self.defaultStr[0](self)
        else:
            ret = self.defaultStr(self)
        return str(ret)

    def __repr__(self):
        return "TimeStampAccumVal(v:%s,t:%s)" % (self.v, self.t)

nested_pickle(TimeStampAccumVal)


class AccumMultiVal:
    def __init__(self, names, *args, **kwargs):
        self.names = names
        v = []
        for arg in args:
            a = listify(arg)
            v.extend(a)
        if len(v) != len(names):
            raise RuntimeError("AccumMultiVal init must have same number of values"
                               "as names, names: %s, values: %s" % (names, v))
        self.v = [tuple(v)]

    def __iadd__(self, other):
        if not isinstance(other, AccumMultiVal):
            raise RuntimeError("__iadd__ must be on two AccumMultiVal instances")
        if other.names != self.names:
            for i in range(0, len(self.names)):
                if self.names[i] != other.names[i]:
                    print(("This is the different Key " + other.names[i]))
            raise RuntimeError("__iadd__ on AccumMultiVal must use same nameset on both instances")
        self.v += other.v

        return self

    def positionList(self, index=0, name=None):
        "returns a list of a single position from every entry, either by name or index"
        if name is not None:
            index = self.names.index(name)
        return [val[index] for val in self.v]

    def getEntryDict(self, index):
        "returns a single entry as a dict indexed by name"
        return dict(zip(self.names, self.v[index]))

    def getDictFormat(self):
        returnDict = {}
        for name in self.names:
            returnDict[name] = []

        for v in self.v:
            for name in self.names:
                returnDict[name].append(v[self.names.index(name)])

        return returnDict

    def max(self, *args, **kwargs):
        return max(self.positionList(*args, **kwargs))

    def min(self, *args, **kwargs):
        return min(self.positionList(*args, **kwargs))

    def mean(self, *args, **kwargs):
        return sum(self.positionList(*args, **kwargs))/len(self.v)

    def stdv(self, *args, **kwargs):
        vp = self.positionList(*args, **kwargs)
        m = self.mean(*args, **kwargs)
        if len(self.v) > 1:
            return math.sqrt(sum([(c-m)*(c-m) for c in vp])/(len(self.v)-1))
        else:
            return 0.0

    def count(self):
        return len(self.v)

    def __float__(self):
        return float(0.0)

    def __str__(self):
        return "(AccumMultiVal-%d Entries, titles: %s)" % (self.count(), self.names)

    def __repr__(self):
        return "AccumMultiVal(v:%s)" % self.v

    def packWKeys(self):
        stringList = []
        # put the number of names
        stringList.append(struct.pack('i', len(self.names)))
        # put the names
        for i in range(0, len(self.names)):
            formatString = "<i" + str(len(self.names[i])) + "s"
            s = struct.Struct(formatString)
            packList = [len(self.names[i]), self.names[i].encode('utf-8')]
            stringList.append(s.pack(*packList))
        # put the values
        formatString = "<" + "f"*len(self.names)
        s = struct.Struct(formatString)
        for v in self.v:
            vfloat = [float(x) for x in v]
            stringList.append(s.pack(*vfloat))
        return "".join(stringList)

    @staticmethod
    def fromPackedStringWHeaders(packedString, **kwargs):
        nameLength = struct.unpack_from('i', packedString)[0]
        offInt = struct.calcsize('i')
        count = offInt
        amv = None
        names = []
        # extract the Names
        for i in range(0, nameLength):  # @UnusedVariable
            sLength = struct.unpack_from('i', packedString, count)[0]
            count += offInt
            formatString = "<" + str(sLength) + "s"
            names.append(struct.unpack_from(formatString, packedString, count)[0])
            count += struct.calcsize(formatString)
        while count < len(packedString):

            formatString = "<"+"f"*nameLength
            s = struct.Struct(formatString)
            unpackList = s.unpack_from(packedString, count)
            count += struct.calcsize(formatString)
            if amv is None:
                amv = AccumMultiVal(names, unpackList)
            else:
                amv.v.append(unpackList)
        return amv

    def pack(self):
        formatString = "<" + "f" * len(self.names)
        s = struct.Struct(formatString)
        stringList = []
        for v in self.v:
            stringList.append(s.pack(*v))
        return string.join(stringList, "")

    @staticmethod
    def fromPackedString(names, packedString, **kwargs):
        l = len(names)
        byteCount = 4 * l
        formatString = "<" + "f" * l
        s = struct.Struct(formatString)

        # get the first val set so we can call the constructor
        v = s.unpack_from(packedString)

        amv = AccumMultiVal(names, v)
        for offset in xrange(byteCount, len(packedString), byteCount):
            amv.v.append(s.unpack_from(packedString, offset))
        return amv

nested_pickle(AccumMultiVal)


class TagAwareDict(MutableMapping):
    def __str__(self):
        return "<TagAwareDict %s>" % self.map

    def __repr__(self):
        return self.__str__()

    def __init__(self, specialType, tagMethodPairList, innerDict=None):
        self.specialType = specialType
        self.tagMethodPairs = tagMethodPairList
        if innerDict is None:
            self.map = {}
        else:
            self.map = innerDict

    def copy(self):
        return TagAwareDict(self.specialType, self.tagMethodPairs, innerDict=self.map.copy())

    def __len__(self):
        nSpecial = sum([isinstance(v, self.specialType) for v in self.map.values()])
        return self.map.__len__() + (len(self.tagMethodPairs) - 1) * nSpecial

    def __contains__(self, k):
        if k in self.map:
            return True
        else:
            try:
                v = None
                for tag, mthd in self.tagMethodPairs:  # @UnusedVariable
                    if k.endswith(tag):
                        v = self.map[k[:-len(tag)]]
                        break
                if v is None:
                    return False
                else:
                    return isinstance(v, self.specialType)
            except KeyError:
                return False

    def __iter__(self):
        i = iter(self.map)
        l = []
        k = None
        while True:
            if k is None:
                k = i.next()  # This will raise StopIteration when we're done
                if isinstance(self.map[k], self.specialType):
                    l = [t for t, m in self.tagMethodPairs[1:]]  # @UnusedVariable
                    yield k+self.tagMethodPairs[0][0]  # key + first tag
                else:
                    ov = k
                    k = None
                    yield ov
            else:
                s = l.pop(0)
                result = k + s
                if len(l) == 0:
                    k = None
                yield result

    def __getitem__(self, k):
        try:
            return self.map.__getitem__(k)
        except KeyError, e:
            for tag, mthd in self.tagMethodPairs:
                if k.endswith(tag):
                    v = self.map[k[:-len(tag)]]
                    if isinstance(v, self.specialType):
                        return mthd(v)
                    else:
                        raise e
            raise e

    def __setitem__(self, k, v):
        return self.map.__setitem__(k, v)

    def __delitem__(self, k):
        """
        Set things up so that if the first tag is given for an instance of self.specialType, the
         value is deleted; otherwise attempts to delete self.specialType instances are ignored.
        """
        try:
            self.map.__delitem__(k)
        except KeyError, e:
            liveTag = self.tagMethodPairs[0][0]
            if k.endswith(liveTag):
                v = self.map[k[:-len(liveTag)]]
                if isinstance(v, self.specialType):
                    return self.map.__delitem__(k[:-len(liveTag)])
                else:
                    raise e
            elif any([k.endswith(s) for s in [tag for tag, mthd  # @UnusedVariable
                                              in self.tagMethodPairs[1:]]]):
                pass
            else:
                raise e

    @staticmethod
    def _mthdToTuple(mthd):
        result = (mthd.im_class, mthd.__func__.__name__)
        # print 'encoding: %s -> %s'%(mthd,result)
        return result

    @staticmethod
    def _tupleToMthd(tpl):
        result = getattr(tpl[0], tpl[1])
        # print 'decoding: %s -> %s'%(tpl,result)
        return result

    def __getstate__(self):
        state = self.__dict__.copy()
        newPairs = []
        for a, b in state['tagMethodPairs']:
            if isinstance(b, types.MethodType):
                newPairs.append((a, self._mthdToTuple(b)))
            else:
                newPairs.append((a, b))
        state['tagMethodPairs'] = newPairs
        return state

    def __setstate__(self, state):
        for k, v in state.items():
            if k == 'tagMethodPairs':
                newPairs = []
                for a, b in v:
                    if isinstance(b, types.TupleType):
                        newPairs.append((a, self._tupleToMthd(b)))
                    else:
                        newPairs.append((a, b))
                setattr(self, 'tagMethodPairs', newPairs)
            else:
                setattr(self, k, v)
