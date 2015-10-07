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

__doc__=""" util.py
This module holds miscellaneous utility functions that do not have
a natural home elsewhere.
"""

_hermes_svn_id_="$Id: util.py 2262 2015-02-09 14:38:25Z stbrown $"

import sys,os,os.path,math,types,random,StringIO,re,weakref,unittest,cStringIO,cPickle,json
import codecs,locale
import ipath
from collections import MutableMapping
import globals
import zipfile
import tempfile
import multiprocessing
import debuggingrng
import struct
import string


_poissonApproxLimit= 50

def getGoogleDirectionsDistanceLatLon(lat1,lng1,lat2,lng2,fallback=True,factor=1.60,speed=50):
    import simplejson,urllib,time
    
    url = 'http://maps.googleapis.com/maps/api/directions/json?origin='+\
	  str(lat1)+','+str(lng1)+'&destination='+str(lat2)+','+str(lng2)+'&sensor=false'
    result = simplejson.load(urllib.urlopen(url))
    #print url
    #print result['status']
    time.sleep(1.5)
    if result['status'] != "OK":
        print "%f,%f: %f,%f"%(lat1,lng1,lat2,lng2)
        print "Result is not ok" + str(result)
        distance = longitudeLatitudeSep(lng1,lat1,lng2,lat2)*factor
        return (distance,distance/speed)
    else:
        return (float(result['routes'][0]['legs'][0]['distance']['value'])/1000.0,float(result['routes'][0]['legs'][0]['duration']['value'])/3600.0)

def longitudeLatitudeSep(lon1,lat1,lon2,lat2):
    "Inputs are in floating point degrees.  Returns separation in kilometers"
    scale= lat1r= lat2r= lon1r= lon2r= a= b= 0.0
    try:
        scale= math.pi/180.
        lat1r = lat1*scale
        lon1r = lon1*scale
        lat2r = lat2*scale
        lon2r = lon2*scale

        a = math.sin(lat1r)*math.sin(lat2r)
        b = math.cos(lat1r)*math.cos(lat2r) * math.cos(lon2r-lon1r)
        apb = a+b
        if apb>1.0: apb = 1.0 # avoid rounding error
        if apb<-1.0: apb = -1.0 # avoid rounding error
        c = math.acos(apb)
    except Exception,e:
        print 'longitudeLatitudeSep: <%s> <%s> <%s> <%s> -> %s %s -> %s %s'%\
            (lon1,lat1,lon2,lat2,lat1r,lat2r,a,b)
        raise e
    R= 6378. # radius of earth in km; in miles it's 3963.189
    return R*c

def _castToFloatHighWater(v):
    if v is None or v=='NA':
        return True, 0.0
    elif type(v)==StatVal:
        return True, v.max()
    elif type(v)==HistoVal:
        return True, v.max()
    else:
        try:
            return True, float(v)
        except:
            return False, None

def _castToIntHighWater(v):
    if v is None or v=='NA':
        return True, 0
    elif type(v)==StatVal:
        return False, None # it's probably an error to see a StatVal in this context
    elif type(v)==HistoVal:
        return False, None # it's probably an error to see a HistoVal in this context
    else:
        try:
            return True, int(v)
        except:
            return False, None

def filteredWriteCSV( ofile, keyList, recDictListOriginal, delim=",", quoteStrings=False ):
    """
    This applies appropriate type casts based on key name and then invokes csv_tools.writeCSV()
    """
    import storagetypes # delayed import to facilitate setting flags in globals at startup time
    from csv_tools import writeCSV, castColumn # delayed import to avoid a dependency loop
    recDictList= [d.copy() for d in recDictListOriginal]
    revisedKeyList = []
    for k in keyList:
        lowerK= unicode(k).lower()


        ##################
        #
        #  put in 3rd class of things that should not be output at all



        if lowerK in storagetypes.storageTypeNames \
            or any([lowerK.endswith(s) for s in ['vol', 'fill', 'frac',
                                                 'km', 'days', 'ratio',
                                                 'ratio_multival', 'times_multival',
                                                 'vol_used', 'vol_used_time',
                                                 'timestamp','availability','multival',
                                                 '_min','_max','_q1','_q3','_median','_mean','_stdv']]):
            castColumn(recDictList, k, _castToFloatHighWater)
            revisedKeyList.append(k)
        elif any([lowerK.find(s)>=0 for s in ['name', 'type', 'note', 'word',
                                              'function', 'category']]):
            revisedKeyList.append(k)
        elif lowerK.endswith('daysretention'):
            pass # Drop this key
        else:
            castColumn(recDictList, k, _castToIntHighWater)
            revisedKeyList.append(k)
    writeCSV( ofile, revisedKeyList, recDictList, delim, quoteStrings, sortColumn="code" )


# Taken from http://trac.sagemath.org/sage_trac/browser/sage/misc/nested_class.py
# calling nested_pickle() on an class with subclasses should help pickle handle
# the subclasses.
def modify_for_nested_pickle(cls, name_prefix, module):
    import types
    for (name, v) in cls.__dict__.iteritems():
        if isinstance(v, (type, types.ClassType)):
            if v.__name__ == name and v.__module__ == module.__name__ and getattr(module, name, None) is not v:
                # OK, probably this is a nested class.
                dotted_name = name_prefix + '.' + name
                v.__name__ = dotted_name
                setattr(module, dotted_name, v)
                modify_for_nested_pickle(v, dotted_name, module)

def nested_pickle(cls):
    modify_for_nested_pickle(cls, cls.__name__, sys.modules[cls.__module__])
    return cls

class strongRef:
    """
    Use as a replacement for a weakref!
    """
    def __init__(self,ref):
        self.ref = ref()
    def __call__(self):
        return self.ref

def maxStatVal(sv):
    return sv.max()
def textStrStatVal(sv):
    return "StatVal(%r)"%sv.maxval
def meanStatVal(sv):
    return sv.mean()

class StatVal:
    def __init__(self,v,defaultFn=maxStatVal,defaultStr=textStrStatVal):
        self.v= v
        self.count= 1
        self.minval= v
        self.maxval= v
        self.defaultFn = defaultFn
        self.defaultStr = defaultStr
    def setDefaultFn(self,defaultFn=maxStatVal):
        self.defaultFn = defaultFn
    def setDefaultStr(self,defaultStr=textStrStatVal):
        self.defaultStr = defaultStr
    def __iadd__(self,other):
        self.v += other.v
        self.count += other.count
        if self.minval>other.minval:
            self.minval= other.minval
        if self.maxval<other.maxval:
            self.maxval= other.maxval
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
        #return self.maxval
    def __str__(self):
        if isiterable(self.defaultStr):
            ret = self.defaultStr[0](self)
        else:
            ret = self.defaultStr(self)
        return str(ret)
        #return "StatVal(%r)"%self.maxval
    def __repr__(self):
        return "StatVal(%s,%s,%s,%s)"%(self.v,self.count,self.minval,self.maxval)

#BUG Make AccumVal pickle well.  Either do away with function pointers or
# find a way of serializing/deserializing the pointers.
def maxAccumVal(av):
    return max(av.v)
def textStrAccumVal(av):
    return "%r+-%r"%(av.mean(),av.stdv())
def meanAccumVal(av):
    # count cannot be 0 because the constructor takes a val
    if av.meanV is None:
        av.meanV= sum(av.v)/len(av.v)
    return av.meanV

class AccumVal:
    # put max first so I can refer to it later.
    # ARRRRGGGGHHH!!!
    # can't pickle a function

    def textStr(self):
        return "%r+-%r"%(self.mean(),self.stdv())
    def __init__(self,v,defaultFn=maxAccumVal,defaultStr=textStrAccumVal):
        self.v= [float(v)]
        self.meanV= None
        self.stdvV= None
        self.defaultFn = defaultFn
        self.defaultStr = defaultStr
        self._sorted = False
    def setDefaultFn(self,defaultFn=maxAccumVal):
        self.defaultFn = defaultFn
    def setDefaultStr(self,defaultStr=textStrAccumVal):
        self.defaultStr = defaultStr
    def __iadd__(self,other):
        if isinstance(other,AccumVal):
            self.v += other.v
        elif type(other) in [types.IntType,types.FloatType,types.LongType]:
            self.v.append(float(other))
        else:
            raise RuntimeError("Tried to add %s to an AccumType"%repr(other))
        self.meanV= None
        self.stdvV= None
        self._sorted = False
        return self
    def _sort(self):
        self.v.sort()
        self._sorted = True
    def mean(self):
        # count cannot be 0 because the constructor takes a val
        if self.meanV is None:
            self.meanV= sum(self.v)/len(self.v)
        return self.meanV
    def stdv(self):
        m= self.mean() # force the calculation
        if self.stdvV is None:
            if len(self.v)>1:
                self.stdvV= math.sqrt(sum([(c-self.meanV)*(c-self.meanV) for c in self.v])/(len(self.v)-1))
            else:
                self.stdvV= 0.0
        return self.stdvV
    def histogram(self):
        histDict = {}
        for vals in self.v:
            if histDict.has_key(vals):
                histDict[vals] += 1
            else:
                histDict[vals] = 1

        return histDict
    def min(self):
        if not self._sorted: self._sort() # since we are probably sorting anyway
        return self.v[0]
    def max(self):
        if not self._sorted: self._sort() # since we are probably sorting anyway
        return self.v[-1]
    def count(self):
        return len(self.v)
    def median(self):
        if not self._sorted: self._sort()
        return self.v[len(self.v)/2]
    def q1(self):
        if not self._sorted: self._sort()
        return self.v[len(self.v)/4]
    def q3(self):
        if not self._sorted: self._sort()
        return self.v[(3*len(self.v))/4]
        
    def __float__(self):
        if isiterable(self.defaultFn):
            return self.defaultFn[0](self)
        return self.defaultFn(self)
        #return self.max() # for compatibility with StatVal
    def __str__(self):
        if isiterable(self.defaultStr):
            ret = self.defaultStr[0](self)
        else:
            ret = self.defaultStr(self)
        return str(ret)
        #return "%r+-%r"%(self.mean(),self.stdv())
    def __repr__(self):
        return "AccumVal(%s)"%self.v

nested_pickle(AccumVal)

def maxHistoVal(av):
    return av.max()

def textStrHistoVal(av):
    return "%r+-%r"%(av.mean(),av.stdv())

def meanHistoVal(av):
    return av.mean()

class HistoVal(object):
    def textStr(self):
        return "%7g+-%7g"%(self.mean(),self.stdv())
    @staticmethod
    def _prep(item):
        if isinstance(item, types.TupleType):
            assert len(item)==2 and isinstance(item[1], types.IntType), \
                "added invalid tuple %s to HistoVal"%(item)
            return ( float(item[0]), item[1] )
        else:
            return ( float(item), 1 )
    def _quantize(self,pairList):
        invQ = 1.0/self.d['quantum']
        for v,n in pairList:
            if v==0.0:
                self.d['strictly_zero'] += n
            qV = int(math.floor(invQ*v))
            if qV in self.d: self.d[qV] += n
            else: self.d[qV] = n
    def _unquantize(self):
        q = self.d['quantum']
        hQ = 0.5*q
        for k,n in self.d.items():
            if isinstance(k,types.IntType):
                if k == 0:
                    yield (0.0, self.d['strictly_zero'])
                    yield (hQ, n - self.d['strictly_zero'])
                else:
                    yield ((k*q + hQ),n)
    def __init__(self,v,quantum=None,defaultFn=maxHistoVal,defaultStr=textStrHistoVal):
        if quantum is None:
            quantum = 0.5 # half a day
        elif quantum==0.0:
            raise RuntimeError("HistoVal quantum cannot be zero")
        self.d = {'quantum':quantum, 'strictly_zero':0}
        if isinstance(v,types.ListType): self._quantize( [self._prep(x) for x in v] )
        else: self._quantize( [self._prep(v)] )
        self.meanV = None
        self.stdvV = None
        self.countV = None
        self.defaultFn = defaultFn
        self.defaultStr = defaultStr
        self.v = None
    def setDefaultFn(self,defaultFn=maxHistoVal):
        self.defaultFn = defaultFn
    def setDefaultStr(self,defaultStr=textStrHistoVal):
        self.defaultStr = defaultStr
    def __iadd__(self,other):
        if isinstance(other,HistoVal):
            self._quantize(other._unquantize())
        else:
            self._quantize( [self._prep(other)] )
        self.meanV = None
        self.stdvV = None
        self.countV = None
        self.v = None
        return self
    def _sort(self):
        self.v = [(v,n) for v,n in self._unquantize()]
        self.v.sort()
    def count(self):
        if self.v is None: self._sort()
        if self.countV is None:
            self.countV = sum([b for a,b in self.v]) # @UnusedVariable
        return self.countV
    def mean(self):
        if self.v is None: self._sort()        
        if self.v == []: 
            return float('NaN')
        else:
            if self.meanV is None:
                self.meanV= sum([a*b for a,b in self.v])/self.count()
            return self.meanV
    def stdv(self):
        if self.v is None: self._sort()        
        if self.stdvV is None:
            c = self.count()
            m = self.mean()
            if c>1:
                self.stdvV= math.sqrt(sum([b*(a-m)*(a-m) for a,b in self.v])/(c-1))
            else:
                self.stdvV= 0.0
        return self.stdvV
    def histogram(self):
        result = {}
        for v,n in self._unquantize(): result[v] = n
        return result
    def raw(self):
        for a,b in self.histogram().items():
            for _ in range(b):
                yield a
    def min(self):
        if self.v is None: self._sort()        
        if self.v == []:
            return float('Nan')
        else:
            return self.v[0][0]
    def max(self):
        if self.v is None: self._sort()        
        if self.v == []:
            return float('Nan')
        else:
            return self.v[-1][0]
    def median(self,_lim=None):
        if self.v is None: self._sort()        
        if self.v == []:
            return float('NaN')
        else:
            if _lim is None: lim = self.count()/2
            else: lim = _lim
            if lim is None: return float('NaN') # This histo has no entries
            offset = 0
            for a,b in self.v:
                if offset + b >= lim: return a
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
        return "HistoVal(...%d...)"%self.count()
    def __repr__(self):
        return "HistoVal(%s)"%self.count()
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
        for v,n in d.items():
            if v in ['quantum','strictly_zero']: fixedD[v] = n
            else: fixedD[int(v)] = n
        result = HistoVal([])
        result.d = fixedD
        return result
    def __cmp__(self, other):
        return self.d.__cmp__(other.d)

nested_pickle(HistoVal)

def maxTimeStampAccumVal(av):
    return max(av.v)
def textStrTimeStampAccumVal(av):
    return "%r,%r: %r-%r"%(av.minT(),av.maxT(),av.mean(),av.stdv())

class TimeStampAccumVal:
    def max(self):
        return max(self.v)
    def maxT(self):
        return max(self.t)
    def textStr(self):
        return "%r,%r: %r-%r"%(self.minT(),self.maxT(),self.mean(),self.stdv())
    def __init__(self,v,t,defaultFn=maxTimeStampAccumVal,defaultStr=textStrTimeStampAccumVal):
        self.v = [float(v)]
        if isinstance(t,tuple):
            self.t = [(float(t[0]),(float(t[1])))]
        else:
            self.t = [float(t)]
        self.defaultFn = defaultFn
        self.defaultStr = defaultStr
    def __iadd__(self,other):
        if isinstance(other,TimeStampAccumVal):
            self.v += other.v
            self.t += other.t
        elif len(other)==2:
            if type(other[0]) in [types.IntType,types.FloatType,types.LongType]:
                if type(other[1]) in [types.IntType,types.FloatType,types.LongType]:
                    self.v.append(float(other[0]))
                    self.t.append(float(other[1]))
                else:
                    raise RuntimeError("Tried to add %s to a TimeStampAccumVal"%repr(other))
            else:
                raise RuntimeError("Tried to add %s to a TimeStampAccumVal"%repr(other))
        else:
            raise RuntimeError("Tried to add %s to a TimeStampAccumVal"%repr(other))

        return self
    def min(self):
        return min(self.v)
    def minT(self):
        return min(self.t)
    def mean(self):
        return sum(self.v)/len(self.v)
    def stdv(self):
        m = sum(self.v)/len(self.v)
        if len(self.v)>1:
            return math.sqrt(sum([(c-self.mean())*(c-self.mean()) for c in self.v])/(len(self.v)-1))
        else:
            return 0.0
    def count(self):
        return len(self.v)
    def __float__(self):
        return float(0.0)
        #if isiterable(self.defaultFn):
    def __str__(self):
        if isiterable(self.defaultStr):
            ret = self.defaultStr[0](self)
        else:
            ret = self.defaultStr(self)
        return str(ret)
    def __repr__(self):
        return "TimeStampAccumVal(v:%s,t:%s)"%(self.v,self.t)

nested_pickle(TimeStampAccumVal)

class AccumMultiVal:
    def __init__(self, names, *args, **kwargs):
        self.names = names
        v = []
        for arg in args:
            a = listify(arg)
            v.extend(a)
        if len(v) != len(names):
            raise RuntimeError("AccumMultiVal init must have same number of values as names, names: %s, values: %s"%(names, v))
        self.v = [tuple(v)]

    def __iadd__(self, other):
        if not isinstance(other, AccumMultiVal):
            raise RuntimeError("__iadd__ must be on two AccumMultiVal instances")
        if other.names != self.names:
            for i in range(0,len(self.names)):
                if self.names[i] != other.names[i]:
                    print "This is the different Key " + other.names[i]
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
        if len(self.v)>1:
            return math.sqrt(sum([(c-m)*(c-m) for c in vp])/(len(self.v)-1))
        else:
            return 0.0
    def count(self):
        return len(self.v)
    def __float__(self):
        return float(0.0)
    def __str__(self):
        return "(AccumMultiVal-%d Entries, titles: %s)"%(self.count(), self.names)
    def __repr__(self):
        return "AccumMultiVal(v:%s)"%self.v

    def packWKeys(self):
        stringList = []
        ## put the number of names
        stringList.append(struct.pack('i',len(self.names)))
        ## put the names
        for i in range(0,len(self.names)):
            formatString = "<i" + str(len(self.names[i]))+"s"
            s = struct.Struct(formatString)
            packList = [len(self.names[i]),self.names[i].encode('utf-8')]
            stringList.append(s.pack(*packList))
        ## put the values
        formatString = "<" + "f"*len(self.names)
        s = struct.Struct(formatString)
        for v in self.v:
            vfloat = [float(x) for x in v]
            stringList.append(s.pack(*vfloat))
        return "".join(stringList)

    @staticmethod
    def fromPackedStringWHeaders(packedString, **kwargs):
        nameLength = struct.unpack_from('i',packedString)[0]
        offInt = struct.calcsize('i')
        count = offInt
        amv = None
        names = []
        ### extract the Names
        for i in range(0,nameLength):
            sLength = struct.unpack_from('i',packedString,count)[0]
            count+= offInt
            formatString = "<" + str(sLength) + "s"
            names.append(struct.unpack_from(formatString,packedString,count)[0])
            count += struct.calcsize(formatString)
        while count < len(packedString):

            formatString = "<"+"f"*nameLength
            s= struct.Struct(formatString)
            unpackList = s.unpack_from(packedString,count)
            count += struct.calcsize(formatString)
            if amv is None:
                amv = AccumMultiVal(names,unpackList)
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
        return "<TagAwareDict %s>"%self.map

    def __repr__(self):
        return self.__str__()

    def __init__(self,specialType,tagMethodPairList,innerDict=None):
        self.specialType= specialType
        self.tagMethodPairs= tagMethodPairList
        if innerDict is None:
            self.map= {}
        else:
            self.map= innerDict
    def copy(self):
        return TagAwareDict(self.specialType, self.tagMethodPairs, innerDict=self.map.copy())
    def __len__(self):
        nSpecial= sum([isinstance(v,self.specialType) for v in self.map.values()])
        return self.map.__len__() + (len(self.tagMethodPairs)-1)*nSpecial
    def __contains__(self,k):
        if self.map.has_key(k): return True
        else:
            try:
                v= None
                for tag,mthd in self.tagMethodPairs:
                    if k.endswith(tag):
                        v= self.map[k[:-len(tag)]]
                        break
                if v is None: return False
                else: return isinstance(v,self.specialType)
            except KeyError:
                return False
    def __iter__(self):
            i= iter(self.map)
            l= []
            k= None
            while True:
                if k is None:
                    k= i.next() # This will raise StopIteration when we're done
                    if isinstance(self.map[k],self.specialType):
                        l= [t for t,m in self.tagMethodPairs[1:]]
                        yield k+self.tagMethodPairs[0][0] # key + first tag
                    else:
                        ov= k
                        k= None
                        yield ov
                else:
                    s= l.pop(0)
                    result= k+s
                    if len(l) == 0: k= None
                    yield result
    def __getitem__(self,k):
        try:
            return self.map.__getitem__(k)
        except KeyError, e:
            for tag,mthd in self.tagMethodPairs:
                if k.endswith(tag):
                    v= self.map[k[:-len(tag)]]
                    if isinstance(v,self.specialType): return mthd(v)
                    else: raise e
            raise e
    def __setitem__(self,k,v):
        return self.map.__setitem__(k,v)
    def __delitem__(self,k):
        """
        Set things up so that if the first tag is given for an instance of self.specialType, the value is
        deleted; otherwise attempts to delete self.specialType instances are ignored.
        """
        try:
            self.map.__delitem__(k)
        except KeyError,e:
            liveTag= self.tagMethodPairs[0][0]
            if k.endswith(liveTag):
                v= self.map[k[:-len(liveTag)]]
                if isinstance(v,self.specialType):
                    return self.map.__delitem__(k[:-len(liveTag)])
                else: raise e
            elif any([k.endswith(s) for s in [tag for tag,mthd in self.tagMethodPairs[1:]]]):
                pass
            else:
                raise e
    @staticmethod
    def _mthdToTuple(mthd):
        result = (mthd.im_class,mthd.__func__.__name__)
        #print 'encoding: %s -> %s'%(mthd,result)
        return result
    @staticmethod
    def _tupleToMthd(tpl):
        result = getattr(tpl[0],tpl[1])
        #print 'decoding: %s -> %s'%(tpl,result)
        return result
    def __getstate__(self):
        state = self.__dict__.copy()
        newPairs = []
        for a,b in state['tagMethodPairs']:
            if isinstance(b,types.MethodType):
                newPairs.append((a,self._mthdToTuple(b)))
            else:
                newPairs.append((a,b))
        state['tagMethodPairs'] = newPairs
        return state
    
    def __setstate__(self,state):
        for k,v in state.items(): 
            if k=='tagMethodPairs':
                newPairs = []
                for a,b in v:
                    if isinstance(b,types.TupleType):
                        newPairs.append((a,self._tupleToMthd(b)))
                    else:
                        newPairs.append((a,b))
                setattr(self,'tagMethodPairs',newPairs)
            else:
                setattr(self,k,v)

def poisson(lamd,rNG=None):
    """
    return a Poisson-distributed random variable with mean lamd.  If
    rNG (for 'random number generator') is non-null, it is used like
    an instance of random.Random as a source for random numbers.

    The algorithm is due to Knuth.  It's not optimal, but it works.
    """
    if lamd>_poissonApproxLimit:
        # Fall back to normal distribution approximation
        # The corrections are empirical, but they're not bad.
        cor= -0.35
        if rNG is None:
            return int(round(random.gauss(lamd+cor,math.sqrt(lamd+cor))))
        else:
            return int(round(rNG.gauss(lamd+cor,math.sqrt(lamd+cor))))
    else:
        L= math.exp(-lamd)
        k= 0
        p= 1.0
        if rNG is None:
            while True:
                k += 1
                p *= random.random()
                if p<=L: break
        else:
            while True:
                k += 1
                p *= rNG.random()

                if p<=L: break
        #if isinstance(rNG,debuggingrng.DebugRandom): print '#### util.poisson -> %d'%(k-1)
        return k-1

class FileWithGrep(StringIO.StringIO):
    # passing a filename into this breaks the ability of hermes to write outputs
    # to a zip file.  This is currently not used in that manner.  If you want to
    # use it in that manner you should take that into account and find a way of
    # dealing with this problem!
    def __init__(self,fnameOrFile,regex):
        if isinstance(fnameOrFile,types.StringType):
            self.file= open(fnameOrFile,"w")
        else:
            self.file= fnameOrFile
        self.regex= re.compile(regex)
        StringIO.StringIO.__init__(self)
    def write(self,strn):
        ind= strn.find('\n')
        while ind>=0:
            p1= strn[:ind+1]
            StringIO.StringIO.write(self,p1)
            curString= self.getvalue()
            if self.regex.search(curString):
                self.file.write(self.getvalue())
                self.file.flush()
            self.seek(0)
            self.truncate()
            strn= strn[ind+1:]
            ind= strn.find('\n')
        if len(strn)>0:
            StringIO.StringIO.write(self,strn)

class redirectEmpty:
    pass

def redirectInput(zipfileName=None, path=None):
    oldHDP = redirectEmpty()
    try: oldHDP = os.environ['HERMES_DATA_PATH']
    except: pass

    if path is not None:
        if isinstance(path, redirectEmpty):
            try: del(os.environ['HERMES_DATA_PATH'])
            except: pass
        else: os.environ['HERMES_DATA_PATH'] = path

    if zipfileName is not None:
        os.environ['HERMES_DATA_PATH'] = 'zipfile:' + zipfileName

    return oldHDP

def redirectOutput(zipfileName=None, path=None):
    oldHDO = redirectEmpty()
    try: oldHDO = os.environ['HERMES_DATA_OUTPUT']
    except: pass

    if path is not None:
        if isinstance(path, redirectEmpty):
            try: del(os.environ['HERMES_DATA_OUTPUT'])
            except: pass
        else: os.environ['HERMES_DATA_OUTPUT'] = path

    if zipfileName is not None:
        os.environ['HERMES_DATA_OUTPUT'] = 'zipfile:' + zipfileName
        zipfileOutput.initialize_locks()

    return oldHDO

#BUG This doesn't check HERMES_DATA_PATH for 'zipfile:' if there's a dirname present
def getDataFullPath(path, dontPrint = False):
    if len(os.path.dirname(path)) != 0:
        if os.path.exists(path):
            return path
        else:
            raise RuntimeError('Data file not found: %s'%path)
    else:
        if getattr(sys,'frozen',None):
            searchThese= [sys._MEIPASS,'.'] # @UndefinedVariable
        elif os.environ.has_key('HERMES_DATA_PATH'):
            hdp = os.environ['HERMES_DATA_PATH']
            if hdp.startswith('zipfile:'):
                # Verify that the requested file is actually in there
                (trash,zipName) = hdp.split('zipfile:', 1)
                zipHandle = zipfile.ZipFile(zipName,'r')
                if path not in zipHandle.namelist():
                    raise IOError("No such subfile %s in zipfile"%path)
                return hdp
            searchThese= hdp.split(os.pathsep)
            searchThese.reverse()
            searchThese.append(".")
            searchThese.reverse()
        else:
            searchThese= ['.']
    for root in searchThese:
        root = root.strip('"')
        p= os.path.join(root,path)
        #print 'looking for %s'%(p)
        if os.path.exists(p): return p

    msg =  "Hermes failed to find the file %s\n"%path
    msg += "There is likely either a typo in the filename or the HERMES_DATA_PATH variable\n"
    msg += "Hermes looked in the following directories:\n   "
    msg += "\n   ".join(searchThese)
    if not dontPrint:
        print msg
    raise IOError(msg)

class openDataFullPath():
    """
    open an input file using HERMES_DATA_PATH and handling zipfiles if directed
    """
    def __init__(self, name, mode='rU'):
        self.zipHandle = None
        fqName = getDataFullPath(name)
        if not fqName.startswith('zipfile:'):
            self.fh = open(fqName, mode)
            return
        if mode == 'rb': mode = 'r'
        if mode not in ['r', 'rU', 'U']:
            raise RuntimeError('mode %s is invalid in openDataFullPath')
        (trash,zipName) = fqName.split('zipfile:', 1)
        self.zipHandle = zipfile.ZipFile(zipName,'r')
        self.fh = self.zipHandle.open(name, mode)

    def getFileHandle(self):
        return self.fh

    def __enter__(self):
        return self.fh

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        if self.zipHandle:
            self.zipHandle.close()
            return
        self.fh.close()



def readRecords(name, recType):
    if os.environ.has_key('HERMES_DATA_PATH'):
        hdp = os.environ['HERMES_DATA_PATH']
        if hdp.startswith('database:'):
            return readRecordsFromDB(name, recType)

    from csv_tools import parseCSV # delayed import to avoid a dependency loop
    return parseCSV(name)

def readRecordsFromDB(name, recType):
    pass

class openFileOrHandle():
    """
    usable when you have either a filename or a filehandle and don't want to know which.
    Only use this in the context handler case (ie "with openFileOrHandle() as f:")
    """
    def __init__(self, file, mode='rU'):
        self.handle = None
        self.odfHandle = None
        if not isinstance(file, types.StringTypes):
            self.handle = file
            return
        if 'w' in mode:
            self.odfHandle = openOutputFile(file, mode)
            self.handle = self.odfHandle
        else:
            self.odfHandle = openDataFullPath(file, mode)
            self.handle = self.odfHandle.getFileHandle()

    def __enter__(self):
        return self.handle

    def __exit__(self, type, value, traceback):
        if self.odfHandle is not None:
            self.odfHandle.close()


class zipfileOutput():
    """
    Context manager for opening the output zipfile

    if we are using multiprocessing or multithreading then initialize_locks
    should be called before any processes fork or threads start.  Non-fillial
    processes should not be accessing the same output zipfile.  Doing so is an
    error.

    given my drothers I'd use flock() but since that doesn't work in all places
    (windows, nfs), I've swapped out the flock calls with multiprocessing.Lock
    which requires that the locks need initialized before initially called.
    because I'm that way, I'll use Lock in place of flock()

    I could argue that I should use three separate context managers for this
    since if one of these fails, things don't work so well.  On the other hand
    if any one of these things fail the zipfile is largely toast.
    """
    lock = None

    @classmethod
    def initialize_locks(cls):
        if cls.lock is None:
            cls.lock = multiprocessing.Lock()

    def __init__(self, zipName, write=True):
        self.zf = None
        self.locked = False
        self.z = None
        # create the zipfile if it doesn't exist.  Use append mode so
        # race conditions don't clobber each other.
        if not os.path.exists(zipName):
            with open(zipName, "a") as zf:
                pass

        # open the file.  Mode must be 'r+b' for zipfile to successfully
        # insert files into an extant zip archive.
        # before we let zipfile touch the file though we should lock it
        if write: mode = 'r+b'
        else: mode = 'rb'
        self.zf = open (zipName, mode)
        if zipfileOutput.lock is not None:
            zipfileOutput.lock.acquire()
            self.locked = True
        if write: mode = 'a'
        else: mode = 'r'
        # What The ever loving F***??!?
        # From python documentation chapter 12.4.1. ZipFile Objects
        # under the compression argument: "The default is ZIP_STORED"
        self.z = zipfile.ZipFile(self.zf, mode, zipfile.ZIP_DEFLATED)

    def __enter__(self):
        return self.z

    def __exit__(self, type, value, traceback):
        if self.z is not None:
            self.z.close()
        if self.locked:
            if zipfileOutput.lock is not None:
                zipfileOutput.lock.release()
        if self.zf is not None:
            self.zf.close()


class openOutputFile():
    """
    open an output file, honoring HERMES_DATA_OUTPUT environment variable.

    This should only be used with things that create a new file.
    currently only supports non-existant (where it opens a normal file)
    or zipfile:<zipfilename> where it will create an output file in the
    specified zip file.

    if a zipfile is created, then this _really_ wants to get closed.
    if at all possible use the "with openOutputFile()" syntax.
    """
    outfileNum = 0

    def __init__(self, name, mode='w', useTempFile = False):
        self.num = openOutputFile.outfileNum
        openOutputFile.outfileNum += 1
        #print "opening %d"%self.num
        self.type = 'closed'
        if not os.environ.has_key('HERMES_DATA_OUTPUT'):
            self.fh = open(name, mode)
            self.name = self.fh.name
            self.type = 'filehandle'
            self.encoding = self.fh.encoding
            return
        hdo = os.environ['HERMES_DATA_OUTPUT']
        if hdo.startswith('zipfile:'):
            (trash, self.zipname) = hdo.split('zipfile:', 1)
            self.name = os.path.basename(name)
            if useTempFile:
                self.type = 'zipfileTemp'
                (self.fd,self.tempfileName) = tempfile.mkstemp('hermes_tmp')
                self.fh = os.fdopen(self.fd, mode)
                self.encoding = self.fh.encoding
            else:
                self.type = 'zipfile'
                self.fh = StringIO.StringIO()
                self.encoding = 'ascii' # a weakness of StringIO
            return
        raise RuntimeError('invalid HERMES_DATA_OUTPUT string %s'%hdo)

    def getFileHandle(self):
        return self.fh

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def write(self, string):
        if isinstance(string,types.UnicodeType):
            self.fh.write(string.encode('utf-8'))
        else:
            self.fh.write(string)
    
    def writelines(self, strings):
        self.fh.writelines([s.encode('utf-8') if isinstance(s,types.UnicodeType) else s for s in strings])

    def flush(self):
        self.fh.flush()

    def close(self):
        if self.type == 'filehandle':
            #print "closing %d"%self.num
            self.fh.close()
            self.type = 'closed'
            return
        if self.type == 'zipfile' or self.type == 'zipfileTemp':
            #print "closing %d"%self.num
            with zipfileOutput(self.zipname) as z:
                if self.type == 'zipfile':
                    data = self.fh.getvalue()
                    self.fh.close()
                    if isinstance(data, types.UnicodeType):
                        z.writestr(self.name, data.encode('utf-8'))
                    else:
                        z.writestr(self.name, data)
                else:
                    self.fh.close()
                    # since the above line closes an fdopen file descriptor
                    # don't do the following line
                    #os.close(self.fd)
                    z.write(self.tempfileName, self.name)
                    os.unlink(self.tempfileName)
            self.type = 'closed'
            
    def tell(self):
        return self.fh.tell()

    def __del__(self):
        self.close()


class openOutputFileForRead():
    """
    open an output file for reading, honoring HERMES_DATA_OUTPUT environment variable.

    This should only be used to read an output file(yes) that was created
    on this run.
    """
    def __init__(self, name, mode="rU"):
        self.type = 'closed'
        if not os.environ.has_key('HERMES_DATA_OUTPUT'):
            self.fh = open(name, mode)
            self.type = 'filehandle'
            return
        hdo = os.environ['HERMES_DATA_OUTPUT']
        if hdo.startswith('zipfile:'):
            name = os.path.basename(name)
            (trash, zipname) = hdo.split('zipfile:', 1)
            with zipfileOutput(zipname, write=False) as z:
                data = z.read(name)

            self.fh = StringIO.StringIO(data)
            return
        raise RuntimeError('invalid HERMES_DATA_OUTPUT string %s'%hdo)

    def getFileHandle(self):
        return self.fh

    def __enter__(self):
        return self.fh

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        if self.type == 'filehandle' or self.type == 'zipfile':
            self.fh.close()
            self.type = 'closed'

    def __del__(self):
        self.close()


class PushbackIterWrapper:
    def __init__(self,iter):
        self.innerIter= iter
        self.pushList= []
    def __iter__(self):
        return self
    def next(self):
        try:
            return self.pushList.pop()
        except IndexError:
            return self.innerIter.next()
    def pushback(self,thing):
        self.pushList.append(thing)

class RandomRounder:
    """
    A Class to handle rounding numbers with random stochasicity
    This class allows for an assigned random seed so that reproducibility
    can be maintained
    """
    def __init__(self,seed=None,debug=False):
        if debug:
            if isinstance(debug,types.StringType): debugName = debug
            else: debugName="debugrandom"
            self.rndm = debuggingrng.DebugRandom(debugName)
        else:
            self.rndm = random.Random()
        ## By default, if this is not set, then system time is used
        self.rndm.seed(seed)

    def round(self,number):
        if not isinstance(number,float):
            return int(number)

        if number % 1 == 0.0:
            return int(number)
        if self.rndm.random() > (number % 1):
            return int(math.floor(number))
        else:
            return int(math.ceil(number))


def isiterable(c):
    "simple test for iterability"
    if hasattr(c, '__iter__') and callable(c.__iter__):
        return True
    return False

def listify(v, keepNone = False):
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

    def __exit__(self,b,c,d):
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

def logDebug(sim, msgOrCallable, *argv):
    """
    This is a minimally featured debug logger that will likely be updated.
    """
    if sim.debug or sim.verbose:
        if callable(msgOrCallable):
            print msgOrCallable(sim, argv)
        else:
            print msgOrCallable

def logVerbose(sim, msgOrCallable, *argv):
    """
    This is a minimally featured verbose logger that will likely be updated.
    """
    if sim.verbose:
        if callable(msgOrCallable):
            print msgOrCallable(sim, argv)
        else:
            print msgOrCallable

def getPreferredOutputEncoding(baseEncoding=None):
    if baseEncoding is None: 
        outEncoding = locale.getpreferredencoding()
    else:
        outEncoding = baseEncoding
    outEncoding = outEncoding.lower().replace('-','')
    encodingMap = {
                   'cp65001':'cp1252', # Windows PowerShell
                   'windows1252':'cp1252',
                   }
    if outEncoding in encodingMap: outEncoding = encodingMap[outEncoding]
    try:
        codecs.lookup(outEncoding)
    except:
        outEncoding = 'utf8'
    return outEncoding


def parseInventoryString(invStr,enableFloat=False):
    """
    An inventory string is a string of the form '7*THING_TYPE+OTHER_TYPE' - a string of fields separated
    by '+' signs.  Each field consists of either a bare type name or an integer followed by '*' followed
    by a bare type name.

    The return value of this function is a list of tuples of the form (count,typeName).  For example,
    the return value of parsing '7*THING_TYPE+OTHER_TYPE' would be [(7,'THING_TYPE'),(1,'OTHER_TYPE')]
    """
    #print 'invStr for %s: %s'%(rec['NAME'],invStr)
    resultList = []
    if invStr is not None and invStr not in  ['','None']:
        invWords= invStr.split('+')
        for word in invWords:
            bits= word.split('*')
            if len(bits)==2:
                if enableFloat:
                    resultList.append((float(bits[0]), bits[1].strip()))
                else:
                    resultList.append((int(bits[0]), bits[1].strip()))
            elif len(bits)==1:
                resultList.append((1,word.strip()))
            else:
                raise RuntimeError('Unparsable Storage description "%s"'%invStr)
    return resultList

def zipper(dir, zip_file):
    '''
    zipper taks the contents of a directory and creates a compressed zip file
    '''
    zip = zipfile.ZipFile(zip_file, 'w', compression=zipfile.ZIP_DEFLATED)
    root_len = len(os.path.abspath(dir))
    for root, dirs, files in os.walk(dir):
        archive_root = os.path.abspath(root)[root_len:]
        for f in files:
            fullpath = os.path.join(root, f)
            archive_name = os.path.join(archive_root, f)
            #print f
            zip.write(fullpath, archive_name, zipfile.ZIP_DEFLATED)
    zip.close()
    return zip_file


def createSubclassIterator(baseclass, filterFunc=None):
    """
    Iterate over all subclasses of the given new-style class
    for which filterFunc(subclass) is True.  If filterFunc
    is not given, assume that all subclasses pass the filter.
    """
    if filterFunc is None:
        def filterFunc(x): return True
    for c in baseclass.__subclasses__():
        if filterFunc(c):
            yield c
        if len(c.__subclasses__()) > 0:
            subIter = createSubclassIterator(c, filterFunc)
            for subC in subIter:
                yield subC




def describeSelf():
    print \
"""
Testing options:

  lon_lat_sep longitude1 latitude1 longitude2 latitude2

     prints separation in kilometers

  poisson floatval

     calculates Poisson-distributed values with mean floatval

  poisson_long

    accumulates many samples near the value where the Poisson
    generator changes from true Poisson to a Gaussian approximation,
    and emits gnuplot data for a histogram.  Typically one would
    pipe the output of this test to a file (named myfile.ascii)
    and then load it in gnuplot with a command like:

     plot "myfile.ascii" using 1:2 with histeps,"myfile.ascii" using 1:3 with histeps;

     or

      plot "myfile.ascii" using 2:3 with points, f(x)=x, f(x)

  teststat

     does simple tests of StatVal

  testaccum

     does simple tests of AccumVal

  testtimestampaccum

     does simple tests of TimeStampAccumVal
     
  testhisto
  
     does simple tests of HistoVal

  filewithgrep

     interactively tests the 'file with interposing grep' class

  getdatapath fname

     looks up fname along the current data file path, as specified by the
     HERMES_DATA_PATH environment variable.  This is a test of getDataFullPath().

  testhdict

     Run some tests on the HDict class

  testtagawaredict

     Run some tests on the TagAwareDict class

  testpushback

     Run some tests on the PushbackIterWrapper class

  testrandrounder

     Run some tests on the RandomRounder class

  parseinventorystring str

     Parse the given inventory string, which should have a form like "7*TYPE_NAME+OTHER_TYPE_NAME"
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
    _testrandindex = ( _testrandindex + 1)%len(_testrandseq)
    return v

def main(myargv=None):
    "Provides a few test routines"
    import ipath

    if myargv is None:
        myargv = sys.argv

    if len(myargv)<2:
        describeSelf()
    elif myargv[1]=="lon_lat_sep":
        if len(myargv)==6:
            lon1= float(myargv[2])
            lat1= float(myargv[3])
            lon2= float(myargv[4])
            lat2= float(myargv[5])
            print "(lat,lon) (%g,%g) to (%g,%g) is %g km"%\
                  (lat1,lon1,lat2,lon2,
                   longitudeLatitudeSep(lon1,lat1,lon2,lat2))
        else:
            print "Wrong number of arguments!"
            describeSelf()

    elif myargv[1]=='poisson':
        if len(myargv)==3:
            lamd= float(myargv[2])
            sum= 0.0
            n= 0
            for i in xrange(10000):
                v= poisson(lamd)
                sum += v
                n += 1
                print v,
                if (i+1)%10 == 0: print ""
            print "mean: %g"%(sum/n)
        else:
            print "Wrong number of arguments!"
            describeSelf()

    elif myargv[1]=='poisson_long':
        if len(myargv)==2:
            bins1= {}
            bins2= {}
            delta= 0.0001
            for i in xrange(1000000):
                v1= poisson(_poissonApproxLimit)
                v2= poisson(_poissonApproxLimit+delta)
                if not bins1.has_key(v1): bins1[v1]= 0
                bins1[v1] += 1
                if not bins2.has_key(v2): bins2[v2]= 0
                bins2[v2] += 1
            for i in xrange(int(2*_poissonApproxLimit+1)):
                if not bins1.has_key(i): bins1[i]= 0
                if not bins2.has_key(i): bins2[i]= 0
                print "%d %d %d"%(i,bins1[i],bins2[i])
        else:
            print "Wrong number of arguments!"
            describeSelf()

    elif myargv[1]=='teststat':
        if len(myargv)==2:
            s= StatVal(0.0)
            print s
            print repr(s)
            for v in [0.37338394029779121, 0.90957338184897241, 0.15996060530020217,
                      0.83193287665351767, 0.05340812724513877, 0.38946846756156384,
                      0.63321268843855927, 0.64064429019556424, 0.29513138953437823,
                      0.83588832473090924]:
                s2= StatVal(v)
                s += s2
            print s
            print repr(s)
        else:
            print "Wrong number of arguments!"
            describeSelf()

    elif myargv[1]=='testaccum':
        if len(myargv)==2:
            randState = random.getstate()
            random.seed(1234)
            _testrandreset()
            s= AccumVal(0.0)
            print s
            print repr(s)
            for i in xrange(5):
                s2= AccumVal(_testrand())
                s += s2
            print repr(s)
            for i in xrange(5):
                s += _testrand()
            print repr(s)
            s2= AccumVal(_testrand())
            for i in xrange(5): s2 += _testrand()
            s += s2
            print repr(s2)
            print repr(s)
            s += s
            print "Histogram = " + repr(s.histogram())
            s= AccumVal(random.gauss(0.5,0.3))
            for i in xrange(1000): s += random.gauss(0.5,0.3)
            print "%d samples supposedly Gaussian(0.5, 0.3):"%s.count()
            print "mean: %7g"%s.mean()
            print "stdv: %7g"%s.stdv()
            print "min: %7g"%s.min()
            print "max: %7g"%s.max()
            print "median: %7g"%s.median()
            random.setstate(randState)
        else:
            print "Wrong number of arguments!"
            describeSelf()

    elif myargv[1]=='testtimestampaccum':
        if len(myargv)==2:
            _testrandreset()
            s = TimeStampAccumVal(0.0,(1.0,4.0))
            print s.t
            print repr(s)
            for i in range(1,5):
                s2 = TimeStampAccumVal(_testrand(),(i,i+1))
                s += s2
            print repr(s)
            for i in range(5,10):
                s += (_testrand(),i)
            print repr(s)
        else:
            print "Wrong number of arguments!"
            describeSelf()

    elif myargv[1]=='testhisto':
        if len(myargv)==2:
            randState = random.getstate()
            random.seed(1234)
            _testrandreset()
            s = HistoVal([random.gauss(0.5,0.3),random.gauss(0.5,0.3)],quantum=0.2)
            print repr(s)
            for i in xrange(100): s += random.gauss(0.5,0.3)
            print "%d samples supposedly Gaussian(0.5, 0.3):"%s.count()
            print "mean: %7g"%s.mean()
            print "stdv: %7g"%s.stdv()
            print "min: %7g"%s.min()
            print "max: %7g"%s.max()
            print "median: %7g"%s.median()
            print "q1: %7g"%s.q1()
            print "q3: %7g"%s.q3()
            print "textstr: %s"%s.textStr()
            hL = [(v,n) for v,n in s.histogram().items()]
            hL.sort()
            print "histogram: { %s }"%', '.join(["%5f: %d"%(v,n) for v,n in hL])
            s1 = HistoVal([0.0, 0.01, 0.0],quantum=0.1)
            hL = [(v,n) for v,n in s1.histogram().items()]
            hL.sort()
            print "adding histoval with histogram { %s }"%', '.join(["%5f: %d"%(v,n) for v,n in hL])
            s += s1
            hL = [(v,n) for v,n in s.histogram().items()]
            hL.sort()
            print "yields { %s }"%', '.join(["%5f: %d"%(v,n) for v,n in hL])
            print 'compare two inequal vals: %s'%(s == s1)
            random.setstate(randState)
            try:
                fakeF = cStringIO.StringIO()
                cPickle.dump(s, fakeF)
                newS = cPickle.loads(fakeF.getvalue())
                print 'pickling and unpickling worked: %s'%newS
            except Exception,e:
                print 'pickling or unpickling failed: %s'%str(e)
            try:
                newS = HistoVal.fromJSON( s.toJSON() )
                print newS.d
                print 'toJSON and fromJSON worked: %s'%newS
                print 'compare two equal vals: %s'%(s == newS)
            except Exception,e:
                print 'toJSON and fromJSON failed: %s'%str(e)
        else:
            print "Wrong number of arguments!"
            describeSelf()

    elif myargv[1]=='filewithgrep':
        if len(myargv)==2:
            regex= raw_input("Enter regular expression > ")
            print "regex is <%s>"%regex
            myfile= FileWithGrep(sys.stdout,regex)
            try:
                while True:
                    strn= raw_input("Next line > ")
                    myfile.write(strn+'\n')
            except EOFError:
                pass
        else:
            describeSelf()

    elif myargv[1]=='getdatapath':
        if len(myargv)==3:
            partialPath= myargv[2]
            fullPath= getDataFullPath(partialPath)
            if fullPath is None:
                print "Could not find full path to <%s>"%partialPath
            else:
                print "<%s> -> <%s>"%(partialPath,fullPath)
        else:
            describeSelf()

    elif myargv[1]=='testhdict':
        if len(myargv)==2:
            try:
                from collections import OrderedDict as HDict
            except ImportError,e:
                try:
                    from odict import OrderedDict as HDict
                except:
                    raise RuntimeError('Ordered dictionary requested but no implementation is available')
            if HDict==dict:
                print "HDict class is unordered dict; tests canceled"
            else:
                print "Yes, it's different."
                d= HDict()
                rng= random.Random()
                rng.seed(1)
                for i in xrange(2000):
                    k= rng.randint(0,1000)
                    d[k]= i
                rng.seed(1)
                alreadySeen= set([])
                testPassed= True
                for i in d.keys():
                    testK= rng.randint(0,1000)
                    while testK in alreadySeen: testK= rng.randint(0,1000)
                    if i!=testK:
                        print 'FAILED: %d != %d on iter %d'%(i,testK,d[i])
                        testPassed= False
                        break
                    alreadySeen.add(testK)
                if testPassed: print 'PASS'
                else: print 'FAIL'
        else:
            describeSelf()
    elif myargv[1] == 'testaccummultival':
        if len(myargv) == 2:
            names = ["foo","bar","baz","qux"]
            values = [(1,2,3,4),(5,6,7,8),(9,10,11,12),(13,14,15,16)]

            amv = AccumMultiVal(names,values[0])
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
            d= TagAwareDict(AccumVal, [('_ave',AccumVal.mean),
                                       ('_stdv',AccumVal.stdv),
                                       ('_min',AccumVal.min),
                                       ('_max',AccumVal.max),
                                       ('_median',AccumVal.median),
                                       ('_count',AccumVal.count)],
                            innerDict={'baz':37.2})
            d["foo"]= 7
            d["bar"]= AccumVal(9)
            d["bar"] += 12
            d["bar"] += 13
            d["bar"] += 8
            d["bar"] += 8

            print "repr: " + repr(d["bar"])
            print "str: " + str(d["bar"])
            print "ave, stdv, min, max, median, count: %s"%[d["bar"+s] for s in ['_ave','_stdv','_min','_max','_median','_count']]
            print "length should be 7: %d"%len(d)
            print "testing 'in' for ['foo','bar_ave','bar_stdv','bar_min','bar_max','bar_median','bar_count','bar_zz']: %s"%\
                [k in d for k in ['foo','bar_ave','bar_stdv','bar_min','bar_max','bar_median','bar_count','bar_zz']]
            print "testing 'in' for ['foo_ave','foo_stdv','foo_min','foo_max','foo_median','foo_count']: %s"%\
                [k in d for k in ['foo_ave','foo_stdv','foo_min','foo_max','foo_median','foo_count']]
            print "testing 'in' for ['blrfl','blrfl_ave','blrfl_stdv','blrfl_min','blrfl_max','blrfl_median','blrfl_count']: %s"%\
                [k in d for k in ['blrfl','blrfl_ave','blrfl_stdv','blrfl_min','blrfl_max','blrfl_median','blrfl_count']]

            i= iter(d)
            try:
                while True:
                    print 'next yields '+i.next()
            except StopIteration:
                print "StopIteration happened"
            print "items: %s"%d.items()
            for k in d.keys(): del d[k]
            print "items after deletes: %s"%d.items()

        else:
            describeSelf()

    elif myargv[1]=='testpushback':
        if len(myargv)==2:
            pbi= PushbackIterWrapper(xrange(7).__iter__())
            count= 1
            while True:
                try:
                    v= pbi.next()
                    print "%d: %s"%(count,v)
                    if count==2:
                        pbi.pushback('two')
                    elif count==5:
                        pbi.pushback('five_1')
                        pbi.pushback('five_2')
                    elif count==6:
                        pbi.pushback('six')
                    count += 1
                except StopIteration:
                    print "got StopIteration"
                    break
        else:
            describeSelf()

    elif myargv[1]=='testrandomrounder':
        if len(myargv)==2:
            randround= RandomRounder()
            x = 7.5
            highcount = 0
            lowcount = 0
            print "Running 10000000 rounding computations on 7.5"
            for i in range(10000000):
                y = randround.round(x)
                if y == 7:
                    lowcount += 1
                elif y == 8:
                    highcount += 1
                else:
                    print "FAILED: RandomRounder, got a result that is incorrect of %d"%y
                    break

            print "The Results low = %d and high = %d should roughly be the same"%(lowcount,highcount)
        else:
            describeSelf()

    elif myargv[1]=='parseinventorystring':
        if len(myargv)==3:
            resultTuple = parseInventoryString(myargv[2])
            print resultTuple
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

    def test_randomrounder(self):
        readBack= self.getReadBackBuf(['dummy','testrandomrounder'])
        myStr= readBack.readlines()[1]
        words = myStr.split()
        l= float(words[4])
        h= float(words[8])
        self.assertTrue(abs((l-h)/(l+h)) < 0.01)

    def test_poisson(self):
        readBack= self.getReadBackBuf(['dummy','poisson','3.5'])
        myStr= readBack.readlines()[-1]
        words = myStr.split()
        v= float(words[-1])
        self.assertTrue(abs((v-3.5)/3.5) < 0.02)

    def test_pushback(self):
        correctStr = """1: 0
2: 1
3: two
4: 2
5: 3
6: five_2
7: six
8: five_1
9: 4
10: 5
11: 6
got StopIteration
        """
        readBack= self.getReadBackBuf(['dummy','testpushback'])
        correctRecs = cStringIO.StringIO(correctStr)
        for a,b in zip(readBack.readlines(), correctRecs.readlines()):
            self.assertTrue(a.strip() == b.strip())

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
        readBack= self.getReadBackBuf(['dummy','testtagawaredict'])
        correctRecs = cStringIO.StringIO(correctStr)
        for a,b in zip(readBack.readlines(), correctRecs.readlines()):
            self.assertTrue(a.strip() == b.strip())

    def test_hdict(self):
        correctStr = """Yes, it's different.
PASS
        """
        readBack= self.getReadBackBuf(['dummy','testhdict'])
        correctRecs = cStringIO.StringIO(correctStr)
        for a,b in zip(readBack.readlines(), correctRecs.readlines()):
            self.assertTrue(a.strip() == b.strip())

    def test_lonlat(self):
        correctStr = """(lat,lon) (92.13,71.28) to (48.9,45.67) is 4789.84 km
        """
        readBack= self.getReadBackBuf(['dummy','lon_lat_sep','71.28', '92.13', '45.67', '48.90'])
        correctRecs = cStringIO.StringIO(correctStr)
        for a,b in zip(readBack.readlines(), correctRecs.readlines()):
            self.assertTrue(a.strip() == b.strip())

    def test_statval(self):
        correctStr = """StatVal(0.0)
StatVal(0.0,1,0.0,0.0)
StatVal(0.90957338184897241)
StatVal(5.12260409181,11,0.0,0.909573381849)
        """
        readBack= self.getReadBackBuf(['dummy','teststat'])
        correctRecs = cStringIO.StringIO(correctStr)
        for a,b in zip(readBack.readlines(), correctRecs.readlines()):
            if a.strip() != b.strip():
                print "\nExpected: <%s>"%b.strip()
                print "Got     : <%s>"%a.strip()
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
        readBack= self.getReadBackBuf(['dummy','testtagawaredict'])
        correctRecs = cStringIO.StringIO(correctStr)
        for a,b in zip(readBack.readlines(), correctRecs.readlines()):
            if a.strip() != b.strip():
                print "\nExpected: <%s>"%b.strip()
                print "Got     : <%s>"%a.strip()
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
        readBack= self.getReadBackBuf(['dummy','testaccum'])
        correctRecs = cStringIO.StringIO(correctStr)
        for a,b in zip(readBack.readlines(), correctRecs.readlines()):
            self.assertTrue(a.strip() == b.strip())

    def test_timestampaccum(self):
        correctStr = """[(1.0, 4.0)]
TimeStampAccumVal(v:[0.0],t:[(1.0, 4.0)])
TimeStampAccumVal(v:[0.0, 0.57417, 0.33765, 0.58059, 0.67528],t:[(1.0, 4.0), (1.0, 2.0), (2.0, 3.0), (3.0, 4.0), (4.0, 5.0)])
TimeStampAccumVal(v:[0.0, 0.57417, 0.33765, 0.58059, 0.67528, 0.61572, 0.74997, 0.83605, 0.70498, 0.2629],t:[(1.0, 4.0), (1.0, 2.0), (2.0, 3.0), (3.0, 4.0), (4.0, 5.0), 5.0, 6.0, 7.0, 8.0, 9.0])
        """
        readBack= self.getReadBackBuf(['dummy','testtimestampaccum'])
        correctRecs = cStringIO.StringIO(correctStr)
        for a,b in zip(readBack.readlines(), correctRecs.readlines()):
            self.assertTrue(a.strip() == b.strip())

    def test_filewithgrep(self):
        correctStr = """This line contains foo
This is bar none the dumbest test in this set
        """
        myfile = cStringIO.StringIO()
        greppedFile = FileWithGrep(myfile,"((foo)|(bar))")
        greppedFile.write("This line contains baz\n")
        greppedFile.write("This line contains foo\n")
        greppedFile.write("I really hope this works\n")
        greppedFile.write("This is bar none the dumbest test in this set\n")
        greppedFile.write("blrfl\n")
        readBack = cStringIO.StringIO(myfile.getvalue())
        correctRecs = cStringIO.StringIO(correctStr)
        for a,b in zip(readBack.readlines(), correctRecs.readlines()):
            self.assertTrue(a.strip() == b.strip())

    def test_fileaccess(self):
        if 'HERMES_DATA_PATH' in os.environ:
            oldDataPath = os.environ['HERMES_DATA_PATH']
        else:
            oldDataPath = None
        try:
            os.environ['HERMES_DATA_PATH'] = '.:/tmp/'
            fname = "hermes_unittest_%d.txt"%os.getpid()
            with openOutputFile('/tmp/%s'%fname) as f:
                f.write("This is a test\n")
            try:
                with openDataFullPath(fname) as f:
                    line = f.readline()
                    self.assertTrue(f.name == '/tmp/%s'%fname)
                    self.assertTrue(line == "This is a test\n")
            finally:
                os.remove("/tmp/%s"%fname)
        finally:
            if oldDataPath == None:
                del os.environ['HERMES_DATA_PATH']
            else:
                os.environ['HERMES_DATA_PATH'] == oldDataPath

    def test_zipaccess(self):
        fname = "hermes_unittest_%d.zip"%os.getpid()
        if 'HERMES_DATA_PATH' in os.environ:
            oldDataPath = os.environ['HERMES_DATA_PATH']
        else:
            oldDataPath = None
        try:
            oldHDO = redirectOutput("/tmp/%s"%fname)
            with openOutputFile('test.txt') as f:
                f.write("This is a test\n")
            with openOutputFile('test2.txt') as f:
                f.write("This is also a test\n")
            redirectOutput(None, oldHDO)
            oldHDI = redirectInput("/tmp/%s"%fname)
            try:
                with openDataFullPath('test2.txt') as f:
                    line = f.readline()
                    self.assertTrue(line == "This is also a test\n")
                with openDataFullPath('test.txt') as f:
                    line = f.readline()
                    self.assertTrue(line == "This is a test\n")
            finally:
                redirectInput(None, oldHDI)
            os.environ['HERMES_DATA_PATH'] = 'zipfile:/tmp/%s'%fname
            with openDataFullPath('test2.txt') as f:
                line = f.readline()
                self.assertTrue(line == "This is also a test\n")
            with openDataFullPath('test.txt') as f:
                line = f.readline()
                self.assertTrue(line == "This is a test\n")
        finally:
            if os.path.exists("/tmp/%s"%fname):
                os.unlink("/tmp/%s"%fname)
            if oldDataPath == None:
                del os.environ['HERMES_DATA_PATH']
            else:
                os.environ['HERMES_DATA_PATH'] == oldDataPath

    def test_parseinventorystring(self):
        result = parseInventoryString(' 3*FIRST_TYPE +7*SECONDTYPE+THIRD TYPE')
        self.assertTrue(result == [(3, 'FIRST_TYPE'), (7, 'SECONDTYPE'), (1, 'THIRD TYPE')])

############
# Main hook
############

if __name__=="__main__":
    main()

