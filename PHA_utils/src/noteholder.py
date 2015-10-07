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


__doc__=""" noteholder.py
This module holds miscellaneous utility functions that do not have
a natural home elsewhere.
"""

_hermes_svn_id_="$Id: noteholder.py 879 2012-03-08 16:47:47Z jleonard $"

import sys, os, os.path, math, types, random, StringIO, re, weakref, copy, StringIO, unittest
import util, abstractbaseclasses, csv_tools

class NoteHolderGroup:
    class NoteHolder( abstractbaseclasses.StatProvider ):
        def __init__(self,group):
            self.d= {}
            self.group= group
            
        def addIncNote(self,inDict):
            raise RuntimeError('NoteHolder.addIncNote is deprecated')
#             if self.group.enabled:
#                 for k,v in inDict.items():
#                     if self.d.has_key('inc_'+k) and self.d['inc_'+k] is not None:
#                         self.d['inc_'+k] += v
#                     else:
#                         self.d['inc'+k]= v
        def clearIncNote(self):
            raise RuntimeError('NoteHolder.clearIncNote is deprecated')
#             if self.group.enabled:
#                 for k in self.d.keys():
#                     if k.startswith('inc_'):
#                         self.d[k] = 0
         
        def addNote(self,inDict):
            if self.group.enabled:
                for k,v in inDict.items():
                    if self.d.has_key(k) and self.d[k] is not None:
                        self.d[k] += v
                    else:
                        self.d[k]= v

        def replaceNote(self,inDict):
            if self.group.enabled:
                for k,v in inDict.items():
                    self.d[k] = v
        
        def __getitem__(self,k):
            if self.d.has_key(k):
                return self.d[k]
            else:
                raise RuntimeError("Trying to access the Note: %s, which does not exist"%k)

        def has_key(self,k): return k in self.d
        def __contains__(self,k): return k in self.d
        def keys(self): return self.d.keys()
        
        def __str__(self):
            return "Note: %s"%self.d

        def getDict(self):
            return self.d

        def getStat(self, statNameString):
            if statNameString in self.d:
                return self.d[statNameString]
            else:
                return None

        def getAvailableStatNameList(self):
            """
            Return a list of all valid stat names.
            """
            return self.keys()

    def __init__(self):
        self.refList= []
        self.enabled= True
        
    def createNoteHolder(self):
        nh= NoteHolderGroup.NoteHolder(self)
        self.refList.append(weakref.ref(nh))
        return nh

    def strengthenRefs(self):
        self.refList = [util.strongRef(ref) for ref in self.refList]

    def __deepcopy__(self, memo):
        """
        overloaded so that we can lose the weakrefs to the individual notes.
        """
        if self in memo:
            return memo[self]
        nhc = NoteHolderGroup()
        memo[self] = nhc
        nhc.enabled = self.enabled
        nhc.noteList = []

        nhc.noteList = [copy.deepcopy(ref(), memo) for ref in self.refList]
        nhc.refList = [weakref.ref(nh) for nh in nhc.noteList if nh is not None]
        return nhc

    def enableAll(self):
        self.enabled= True
    
    def disableAll(self):
        self.enabled= False
    
    def writeNotesToResultsEntry(self, shdNet, results):
        recDictList = []
        for n in [ nRef() for nRef in self.refList if nRef() is not None]:
            recDictList.append(n.d)

        results.addReportRecs(shdNet, recDictList)


    def writeNotesAsCSV(self, fnameOrFile, fields=None, requiredFields=None, 
                        overrideFields=None, filtered=True, insertRows=None):
        """
        By default, create the named csv file and write all NoteHolder contents to it.

        If fields is specified, only output those columns.
        If requiredFields is specified, a row must have a value for that field 
            for that row to be output (note that that column doesn't need to be
            a part of the output fields).
        if overrideFields is specified, a note with any field in overrideFields
            will be displayed regardless of "requiredFields"
        if filtered is set then use filteredWriteCSV
        insertRows is a list of rows to be inserted at the top of the file.
            Each row should be a list of values to be inserted.
        """

        requiredFields = util.listify(requiredFields, keepNone = True)
        overrideFields = util.listify(overrideFields)
        keyList = util.listify(fields)
        insertRows = util.listify(insertRows)

        fmtdInsertRows = []
        for row in insertRows:
            fmtd = ""
            for i,val in enumerate(row):
                if i > 0: fmtd += ','
                fmtd += str(val)
            fmtd += '\n'
            fmtdInsertRows.append(fmtd)

        recDictList= []

        for n in [ nRef() for nRef in self.refList if nRef() is not None]:
            if requiredFields is not None:
                if not reduce(lambda keep,field: keep or (field in n.d.keys()),
                              overrideFields,
                              False):
                    if not reduce(lambda keep,field: keep and (field in n.d.keys()),
                                  requiredFields,
                                  True):
                        continue
            if fields is None:
                for k in n.d.keys():
                    if not k in keyList: keyList.append(k)
            recDictList.append(n.d)

        if fields is None:
            keyList.sort()
            if 'code' in keyList: keyList.remove('code')
            if 'name' in keyList: keyList.remove('name')
            keyList= ['code','name'] + keyList


        if filtered:
            writeMethod = util.filteredWriteCSV
        else:
            writeMethod = csv_tools.writeCSV

        if isinstance(fnameOrFile,types.StringType):
            with util.openOutputFile(fnameOrFile,"w") as f:
                for fmtdRow in fmtdInsertRows:
                    f.write(fmtdRow)
                writeMethod(f,keyList,recDictList)
        else:
            for fmtdRow in fmtdInsertRows:
                f.write(fmtdRow)
            writeMethod(fnameOrFile,keyList,recDictList)

    def clearAll(self,keepRegex):
        """
        Clear all keys not matching keepRegex from all NoteHolders in this group.  
        keepRegex can be either a regular expression object (from the 're' package) 
        or a string that can be compiled into a regular expression object.
        """
        if isinstance(keepRegex,types.StringType):
            keepRegex= re.compile(keepRegex)
        for n in [ nRef() for nRef in self.refList if nRef() is not None]:
            for k in n.d.keys():
                if not keepRegex.match(k):
                    del n.d[k]

    def printAll(self,printRegex='.*'):
        """
        Print all keys matching printRegex from all NoteHolders in this group.  
        printRegex can be either a regular expression object (from the 're' package) 
        or a string that can be compiled into a regular expression object.
        """
        if isinstance(printRegex,types.StringType):
            printRegex= re.compile(printRegex)
        for n in [ nRef() for nRef in self.refList if nRef() is not None]:
            tmpD= {}
            for k,v in n.d.items():
                if printRegex.match(k):
                    tmpD[k]= v
            print tmpD

    def getnotes(self):
        """
        get a list of the NoteHolders without the weak references
        in the way.  This will create non-weak references for all of
        the notes so use with caution.
        """
        return [ref() for ref in self.refList]

    def copyNoteHolder(self, noteHolderDict):
        """
        Add a (shallow) copy of the given noteHolder dict to this NoteHolderGroup, and return the
        new NoteHolder.

        To avoid weak reference issues, the argument is the result of noteHolder.getDict(), so the
        call typically looks like 'noteHolderGroup.copyNoteHolder( someNoteHolder.getDict() )' .
        If called with a noteHolder that is already a part of the group, the group will end up with
        two identical copies of the same NoteHolder, both referencing the same notes.
        """
        newNH = self.createNoteHolder()
        newNH.d = noteHolderDict.copy()
        return newNH

util.nested_pickle(NoteHolderGroup)

def describeSelf():
    print \
"""
Testing options:

  testnote

     does simple tests of NoteHolder

"""

def main(myargv=None):
    "Provides a few test routines"

    if myargv is None: 
        myargv = sys.argv
    
    if len(myargv)<2:
        describeSelf()
    elif myargv[1]=='testnote':
        nhg1= NoteHolderGroup()
        nhg2= NoteHolderGroup()
        if len(myargv)==2:
            print "---- creating groups of NoteHolders ----"
            nh1_1= nhg1.createNoteHolder()
            nh1_1.addNote({"int":0, "float":1.0, "word":"hello "})
            print 'nh1_1: '+str(nh1_1)
            nh1_2= nhg1.createNoteHolder()
            nh1_2.addNote({"float":1234.5,"word":"foobar"})
            print 'nh1_2: ' + str(nh1_2)
            print "---- testing addNote ----"
            for i in xrange(10):
                nh1_1.addNote({"int":i,"float":(1.0+0.1*i), "word":"world "})
            print 'nh1_1: ' + str(nh1_1)
            nh2_1= nhg2.createNoteHolder()
            nh2_1.addNote({"float":13243.5,"word":"Iamnh2_1"})
            nh1_1.addNote({"float":6789.0,"word":"foobar"})
            print "---- generating CSV; fake file contents follow ----"            
            stringFile= StringIO.StringIO()
            nhg1.writeNotesAsCSV(stringFile)
            print stringFile.getvalue()
            print "--- printing everything ----"            
            nhg1.printAll()
            nhg2.printAll()
            print "--- printing just 'int' ----"            
            nhg1.printAll('int')
            print "--- clearing all but 'float' from nhg1 ----"
            nhg1.clearAll('float')
            nhg1.printAll()
            nhg2.printAll()
            print "--- testing enable/disable ----"
            nhg1.enableAll()
            nhg2.disableAll()
            for n in [nh1_1, nh1_2, nh2_1]: n.addNote({"test":"ngh1only"})
            nhg1.disableAll()
            nhg2.enableAll()
            for n in [nh1_1, nh1_2, nh2_1]: n.addNote({"test":"ngh2only"})
            nhg1.printAll()
            nhg2.printAll()
        else:
            print "Wrong number of arguments!"
            describeSelf()

    else:
        describeSelf()

class TestNoteHolder(unittest.TestCase):
    def getReadBackBuf(self, wordList):
        try:
            sys.stdout = myStdout = StringIO.StringIO()
            main(wordList)
        finally:
            sys.stdout = sys.__stdout__
        return StringIO.StringIO(myStdout.getvalue())
    
    def compareOutputs(self, correctStr, readBack):
        correctRecs = StringIO.StringIO(correctStr)
        for a,b in zip(readBack.readlines(), correctRecs.readlines()):
            #print "<%s> vs. <%s>"%(a,b)
            self.assertTrue(a.strip() == b.strip())
    
    def test_noteholder(self):
        correctStr = """---- creating groups of NoteHolders ----
nh1_1: Note: {'int': 0, 'float': 1.0, 'word': 'hello '}
nh1_2: Note: {'float': 1234.5, 'word': 'foobar'}
---- testing addNote ----
nh1_1: Note: {'int': 45, 'float': 15.500000000000002, 'word': 'hello world world world world world world world world world world '}
---- generating CSV; fake file contents follow ----
code,name,float,int,word
0,NA,6804,45,hello world world world world world world world world world world foobar
0,NA,1234,0,foobar

--- printing everything ----
{'int': 45, 'float': 6804.5, 'word': 'hello world world world world world world world world world world foobar'}
{'float': 1234.5, 'word': 'foobar'}
{'float': 13243.5, 'word': 'Iamnh2_1'}
--- printing just 'int' ----
{'int': 45}
{}
--- clearing all but 'float' from nhg1 ----
{'float': 6804.5}
{'float': 1234.5}
{'float': 13243.5, 'word': 'Iamnh2_1'}
--- testing enable/disable ----
{'test': 'ngh1only', 'float': 6804.5}
{'test': 'ngh1only', 'float': 1234.5}
{'test': 'ngh2only', 'float': 13243.5, 'word': 'Iamnh2_1'}
        """
        readBack= self.getReadBackBuf(['dummy','testnote'])
        self.compareOutputs(correctStr, readBack)
        


############
# Main hook
############

if __name__=="__main__":
    main()

