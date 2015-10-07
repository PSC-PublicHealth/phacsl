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

_hermes_svn_id_="$Id: csv_tools.py 2262 2015-02-09 14:38:25Z stbrown $"

import sys,os,os.path,math,re,types,chardet,codecs
import ipath
from util import openFileOrHandle, logError, raiseRuntimeError, getPreferredOutputEncoding

verbose= 0
debug= 0

class CSVDict(dict):
    def getFloat(self,keyOrKeyList):
        if isinstance(keyOrKeyList,types.ListType):
            for k in keyOrKeyList:
                if k in self: return float(self[k])
            raise KeyError(keyOrKeyList[-1])
        else:
            return float(self[keyOrKeyList])

    def safeGetFloat(self,keyOrKeyList,default,ignore=None):
        if ignore is None:
            try:
                return self.getFloat(keyOrKeyList)
            except (KeyError, ValueError):
                return default
        else:
            if isinstance(keyOrKeyList,types.ListType):
                for k in keyOrKeyList:
                    if k in self and self[k]!=ignore and self[k]!='':
                        return float(self[k])
                return default
            else:
                if k in self and self[k]!=ignore:
                    return float(self[k])
                return default


def makeSplitRegex(delim):
    """
    This regex should properly handle the following cases:
    * empty strings (adjacent delimiters)
    * quoted strings, single or double
    * internal single or double quotes
    * backslash-escaped internal quotes inside quoted strings
    * delimiters within quoted strings
    * leading and trailing whitespace
    * multiple internal single quotes (apostrophe) inside non-quoted strings
    """
    if delim is None:
        return re.compile(r'\s*(\S+)(?:\s*|$)')
    elif delim=='\t':
        # why is \t delimiter treated separately????
        rstr= r'''[ \n\r\f\v]*([^"'%s]*|"[^"]*"|'[^']*')[ \n\r\f\v]*(?:%s|$)'''%(delim,delim)
        if debug: print "regex for <%s>: <%s>"%(delim,rstr)
        return re.compile(rstr)        
    else:
        # See bug #381 in redmine for more information
        # Note that both double and single quoted string patterns employ a
        # negative lookbehind assertion to allow for escaped quote characters
        dbl_quoted = r'''"[^"]*"(?<!\\)'''
        sgl_quoted = r''''[^']*'(?<!\\)'''
        unquoted = r'''[^%s]*''' % delim
        # this is the capturing group pattern
        group1 = r'''%s|%s|%s''' % (dbl_quoted, sgl_quoted, unquoted)
        # build the regex string
        rstr = r'''\s*(%s)\s*(?:%s|$)''' % (group1, delim)
        # debug logging
        if debug: print "regex for <%s>: <%s>"%(delim,rstr)
        return re.compile(rstr)

def parseCSVHeader(ifile):
    """
    returns just the list of keys from the header of the csv file

    ifile can be any of: an open file handle, a file name, or a tuple of the form (keys, recs)
    equivalent to what parseCSV would return (which is returned blindly)
    """
    if isinstance(ifile, types.TupleType):
        if verbose: print "parsing header of preprocessed tuple instead of CSV"
        return ifile[0]

    if isinstance(ifile, types.StringTypes):
        name = ifile
    else:
        name = ifile.name

    if verbose: print "parsing header of %s"%name
    lineList= []
    possibleDelimiters= [";",",","\t",None] # empty string means whitespace-delimited
    with openFileOrHandle(ifile) as f:
        lines= f.readlines(20) #don't bother reading the entire file, just enough to get hints
    delimFound= 0
    delimForThisFile= None
    for delim in possibleDelimiters:
        if delim is not None and lines[0].find(delim)<0:
            if debug: print "Delim is not <%s> (no occurrences in labels)"%delim
            continue
        tryRegex= makeSplitRegex(delim)
        wordCount= len(tryRegex.findall(lines[0]))
        if wordCount<3: 
            if debug: print "Delim is not <%s> (no labels found)\n"%delim
            continue
        for line in lines[1:]:
            nwords= len(tryRegex.findall(line))
            if nwords>0 and nwords != wordCount:
                print "%d vs. %d: <%s>"%(nwords,wordCount,line)
                if debug: print "Delim is not <%s>\n"%delim
                break
        else:
            delimFound= 1
            delimForThisFile= delim
            regexForThisFile= tryRegex
            break
    if not delimFound:
        raise Exception("Cannot find the right delimiter for this CSV input!")
        #sys.exit("Cannot find the right delimiter for this CSV input!")
    if debug: print"delimForThisFile= <%s>"%delimForThisFile
    keys= regexForThisFile.findall(lines[0])[:-1] # skip empty regex match at end
    keys= [ x.strip() for x in keys ]
    stringsAreQuoted= 1
    for key in keys:
        if len(key)>0 \
                and (not key.startswith('"') or not key.endswith('"')) \
                and (not key.startswith("'") or not key.endswith("'")):
            stringsAreQuoted= 0
    if debug: print "stringsAreQuoted= %d"%stringsAreQuoted
    if stringsAreQuoted:
        keys = [ x[1:-1] for x in keys ]
    return keys

def parseCSV( ifile ):
    """
    returns a tuple containing a list of keys and a list of dicts"

    ifile can be any of: an open file handle, a file name, or a tuple of the form (keys, recs)
    equivalent to what parseCSV would return (which is returned blindly).
    """
    if isinstance(ifile, types.TupleType):
        if verbose: print "parsing preprocessed tuple instead of CSV"
        return ifile

    if isinstance(ifile, types.StringTypes):
        name = ifile
    else:
        name = ifile.name

    if verbose: print "parsing %s"%name
    lineList= []
    possibleDelimiters= [";",",","\t",None] # empty string means whitespace-delimited
    with openFileOrHandle(ifile) as f:
        lines= f.readlines()
    encodingInfo = chardet.detect("".join(lines))
    if encodingInfo['confidence'] >= 0.9: 
        predictedEncoding = encodingInfo['encoding']
        if predictedEncoding == "utf8" or predictedEncoding == "utf-8": predictedEncoding = "utf-8-sig"
        lines = [l.decode(predictedEncoding) for l in lines]
    else:
        predictedEncoding = encodingInfo['encoding']
        if predictedEncoding == "utf8" or predictedEncoding == "utf-8": predictedEncoding = "utf-8-sig"
        lines = [l.decode(predictedEncoding,'replace') for l in lines]
    delimFound= 0
    delimForThisFile= None
    for delim in possibleDelimiters:
        if delim is not None and lines[0].find(delim)<0:
            if debug: print "Delim is not <%s> (no occurrences in labels)"%delim
            continue
        tryRegex= makeSplitRegex(delim)
        wordCount= len(tryRegex.findall(lines[0]))
        if wordCount<3: 
            if debug: print "Delim is not <%s> (no labels found)\n"%delim
            continue
        for line in lines[1:]:
            nwords= len(tryRegex.findall(line))
            if nwords>0 and nwords != wordCount:
                print "%d vs. %d: <%s>"%(nwords,wordCount,line)
                if debug: print "Delim is not <%s>\n"%delim
                break
        else:
            delimFound= 1
            delimForThisFile= delim
            regexForThisFile= tryRegex
            break
    if not delimFound:
        raise Exception("Cannot find the right delimiter for this CSV input!")
        #sys.exit("Cannot find the right delimiter for this CSV input!")
    if debug: print"delimForThisFile= <%s>"%delimForThisFile
    keys= regexForThisFile.findall(lines[0])[:-1] # skip empty regex match at end
    keys= [ x.strip() for x in keys ]
    stringsAreQuoted= 1
    for key in keys:
        if len(key)>0 \
                and (not key.startswith('"') or not key.endswith('"')) \
                and (not key.startswith("'") or not key.endswith("'")):
            stringsAreQuoted= 0
    if debug: print "stringsAreQuoted= %d"%stringsAreQuoted
    if stringsAreQuoted:
        keys = [ x[1:-1] for x in keys ]
    lines= lines[1:]
    lineNum= 1
    for line in lines:
        words= regexForThisFile.findall(line)[:-1] # skip empty regex match at end
        words= [x.strip() for x in words]
        if len(words)>0:
            dict= CSVDict()
            if len(words)!=len(keys):
                eS = "Line length error: %d vs %d"%(len(words),len(keys))
                for i in xrange(len(keys)):
                    eS += "\n%d: <%s> <%s>"%(i,keys[i],words[i])
                logError(eS)
                raiseRuntimeError("Line length error parsing CSV at line %d:"%(lineNum))
                #sys.exit("Line length error parsing CSV at line %d"%(lineNum))
            for i in xrange(len(keys)):
                if (stringsAreQuoted 
                    and ((words[i].startswith('"') 
                          and words[i].endswith('"'))
                         or (words[i].startswith('"') 
                             and words[i].endswith('"')))):
                        dict[keys[i]]= words[i][1:-1]
                else:
                    if len(words[i])>0:
                        if words[i][-1]=='%':
                            try:
                                dict[keys[i]]= 0.01*float(words[i][:-1])
                            except ValueError:
                                dict[keys[i]]= words[i]
                        else:
                            try:
                                dict[keys[i]]= int(words[i])
                            except ValueError:
                                try:
                                    dict[keys[i]]= float(words[i])
                                except ValueError:
                                    dict[keys[i]]= words[i]
                    else:
                        dict[keys[i]]= words[i]

            lineList.append(dict)
        lineNum += 1
    return (keys, lineList)


def writeCSV( ofile, keyList, recDictList, delim=",", quoteStrings=False, sortColumn=None, emptyVal='NA' ):
    """
    Each element of the input recDictList is a dictionary containing
    keys from keyList.
    """
    with openFileOrHandle(ofile, 'w') as rawO:
        o = codecs.getwriter(getPreferredOutputEncoding(rawO.encoding))(rawO,'replace')
        if quoteStrings:
            o.write('"%s"'%keyList[0])
            for key in keyList[1:]:
                o.write('%s"%s"'%(delim,key))
        else:
            o.write("%s"%keyList[0])
            for key in keyList[1:]:
                o.write("%s%s"%(delim,key))
        o.write("\n")
        if sortColumn is not None:
            if sortColumn not in keyList:
                print "Warning: sortColumn specified in  writeCSV is not a valid column, no sorting will be performed."
            else:
                recDictList.sort(lambda x,y:cmp(unicode(x[sortColumn]).lower(),unicode(y[sortColumn]).lower()))
        
        for rD in recDictList:
            try:
                val= rD[keyList[0]]
            except KeyError:
                val= emptyVal
            if isinstance(val,(types.IntType, types.LongType)): o.write("%d"%val)
            elif isinstance(val,float): o.write("%r"%val)
            elif quoteStrings:
                if val.startswith('"') and val.endswith('"'): o.write('%s'%val)
                else: o.write('"%s"'%val)
            else:
                o.write("%s"%val)
            for key in keyList[1:]:
                try:
                    val= rD[key]
                except KeyError:
                    val= emptyVal
                if isinstance(val,(types.IntType, types.LongType)): o.write("%s%d"%(delim,val))
                elif isinstance(val,float): o.write("%s%r"%(delim,val))
                elif quoteStrings:
                    if val.startswith('"') and val.endswith('"'): o.write('%s%s'%(delim,val))
                    else: o.write('%s"%s"'%(delim,val))
                else:
                    o.write("%s%s"%(delim,val))
            o.write("\n")
    if debug:
        print "Wrote %d recs, delim=<%s>, quoteStrings= %s"%\
                  (len(recDictList),delim,quoteStrings)

    
class castTypes:
    "An enumeration of casting types along with methods to attempt to perform them"

    @staticmethod
    def CastInt(val, **kwargs):
        try:
            ret = int(val)
        except:
            return False, val
        return True, ret
    
    @staticmethod
    def CastString(val, **kwargs):
        ### This is not an exhaustive list, so if this bombs on your system, we may need to add
        codecs = ['iso-8859-1','cp1252','latin-1','utf-8']
        if 'predictedEncoding' in kwargs:
            codecs = [kwargs['predictedEncoding']]
        ### This will now cast all strings as UNICODE
        if None == val:
            return False, val
        try:
            if isinstance(val,types.UnicodeType):
                ret = val
            elif isinstance(val,types.StringType):
                ret = None
                for i in codecs:
                    try:
                        dVal = val.decode(i)
                        
                        break
                    except Exception as e:
                        print "%s"%str(e)
                        pass
                try:
                    ret = dVal
                except Exception as e:
                    print "UNICODE FAILED: %s"%str(e)
                    
                if ret is None:
                    ret = unicode(val,'utf-8',errors='replace')   
            else:
                ## Default if it can figure it out.
                ret = unicode(str(val),'utf-8',errors='replace')
        except Exception as e:
            print str(e)
            return False, val
        return True, ret
    
    @staticmethod
    def CastEmpty(val, **kwargs):
        if None == val:
            return True, val
        return False, val
    
    @staticmethod
    def CastLong(val, **kwargs):
        try:
            ret = long(val)
        except:
            return False, val
        return True, ret
    
    @staticmethod
    def CastNA(val, **kwargs):
        if "NA" == val:
            return True, val
        return False, val

    @staticmethod
    def CastFloat(val, **kwargs):
        try:
            ret = float(val)
        except:
            return False, val
        return True, ret
    
    @staticmethod
    def CastNonnegativeInt(val, **kwargs):
        try:
            ret = int(val)
            if ret < 0:
                return False, val
        except:
            return False, val
        return True, ret

    @staticmethod
    def CastPositiveInt(val, **kwargs):
        try:
            ret = int(val)
            if ret < 1:
                return False, val
        except:
            return False, val
        return True, ret

    @staticmethod
    def CastEmptyIsNullString(val, **kwargs):
        if val is None:
            return True, unicode("")
        if val == "":
            return True, unicode("")
        return False, val

    @staticmethod
    def CastEmptyIsZero(val, **kwargs):
        if val is None:
            return True, 0
        if val == "":
            return True, 0
        return False, val

    @staticmethod
    def CastEmptyIsNone(val, **kwargs):
        if val is None:
            return True, None
        if val == "":
            return True, None
        return False, val
    
    @staticmethod
    def CastBoolean(val, **kwargs):
        """This actually returns an int, 1 or 0, rather than python True/False"""
        if val is None:
            return True, 0
        elif isinstance(val, types.StringTypes):
            if val.lower() == 't' or val.lower() == 'true':
                return True, 1
            elif val.lower() == 'f' or val.lower() == 'false':
                return True, 0
            else:
                try:
                    ival = float(val)
                    if ival:
                        return True, 1
                    else:
                        return True, 0
                except ValueError:
                    pass
        if val:
            return True, 1
        else:
            return True, 0

    INT                   = CastInt
    STRING                = CastString
    EMPTY                 = CastEmpty
    LONG                  = CastLong
    NA                    = CastNA
    FLOAT                 = CastFloat
    NONNEGATIVE_INT       = CastNonnegativeInt
    POSITIVE_INT          = CastPositiveInt
    EMPTY_IS_NULL_STRING  = CastEmptyIsNullString
    EMPTY_IS_ZERO         = CastEmptyIsZero
    EMPTY_IS_NONE         = CastEmptyIsNone
    BOOLEAN               = CastBoolean

class castFail(Exception):
    "Exception class called if any member of a column failed its cast"
    def __init__(self, failedVal, key, line, fileName=None):
        self.failedVal = failedVal
        self.key = key
        self.line = line
        self.fileName = fileName
    def __str__(self):
        if self.fileName is None:
            return "*** Failed to cast value: %s for key %s on line %d ***"\
                %(repr(self.failedVal), self.key, self.line)
        else:
            return "*** Failed to cast value: %s for key %s on line %d of file %s ***"\
                %(repr(self.failedVal), self.key, self.line, self.fileName)

def castValue(val, castList, key):
    if isinstance(castList, types.FunctionType):
        castList = [castList]
    for cast in castList:
        status, out = cast(val)
        if status:
            return out
    else:
        print 'castList: %s key: %s val: %s val type: %s'%(castList,key,val,type(val).__name__)
        raise castFail(val, key, -1)

def castEntry(rec, key, castList):
    if isinstance(castList, types.FunctionType):
        castList = [castList]
    
    if key in rec:
        val = rec[key]
    else:
        val = None

    for cast in castList:
        status, out = cast(val)
        if status:
            rec[key] = out
            break
    else:
        raise castFail(val, key, -1)

def castColumn(recs, key, castList, fileName=None):
    """ 
    Cast all entries in a column to a specific (set of) type(s).
    
    Tries each cast type in castList in order on each member of a column 
    until it either succeeds in its casting or (if the list is exhausted)
    throws a castFail exception.
    """
    if isinstance(castList, types.FunctionType):
        castList = [castList]

    for line,rec in enumerate(recs,1):
        if key in rec:
            val = rec[key]
        else:
            val = None

        hints = {}
        if hasattr(rec,'predictedEncoding') and rec.predictedEncoding is not None:
            hints['predictedEncoding'] = rec.predictedEncoding
        for cast in castList:
            status, out = cast(val, **hints)
            if status:
                rec[key] = out
                break
        else:
            raise castFail(val, key, line, fileName)

def main():
    "This is a simple test routine which takes csv files as arguments"
    global verbose, debug
    
    for a in sys.argv[1:]:
        if a=='-v': verbose= True
        elif a=='-d': debug= True
        else:
            print "##### Checking %s"%a
            with open(a,"rU") as f:
                keys,recs= parseCSV(f)
            
            with open('test_csv_tools.csv','w') as f:
                writeCSV(f,keys,recs,quoteStrings=True)
            with open('test_csv_tools.csv','rU') as f:
                keys2,recs2= parseCSV(f)
            assert(keys2==keys)
            for i,tpl in enumerate(zip(recs2,recs)):
                r2,r = tpl
                if r != r2:
                    print "##### record %d differs: "%i
                    for k in keys:
                        if r[k] != r2[k]:
                            print "%s:%s --> %s:%s"%(k,r[k],k,r2[k])
            assert(recs2==recs)
            
############
# Main hook
############

if __name__=="__main__":
    main()

