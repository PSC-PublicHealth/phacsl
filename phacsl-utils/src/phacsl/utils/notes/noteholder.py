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


""" noteholder.py
This module provides a handy mechanism for keeping records within ongoing simulations.
"""

import types
import re
import weakref
import copy
from ..formats import csv_tools
from ..misc import util

strongRef = util.strongRef
listify = util.listify
nested_pickle = util.nested_pickle


class NoteHolderGroup(object):
    class NoteHolder(object):
        def __init__(self, group):
            self.d = {}
            self.group = group

        def addIncNote(self, inDict):
            raise RuntimeError('NoteHolder.addIncNote is deprecated')

        def clearIncNote(self):
            raise RuntimeError('NoteHolder.clearIncNote is deprecated')

        def addNote(self, inDict):
            if self.group.enabled:
                for k, v in inDict.items():
                    if k in self.d and self.d[k] is not None:
                        self.d[k] += v
                    else:
                        self.d[k] = v

        def replaceNote(self, inDict):
            if self.group.enabled:
                for k, v in inDict.items():
                    self.d[k] = v

        def __getitem__(self, k):
            if k in self.d:
                return self.d[k]
            else:
                raise RuntimeError("Trying to access the Note: %s, which does not exist" % k)

        def has_key(self, k):
            return k in self.d

        def __contains__(self, k):
            return k in self.d

        def keys(self):
            return self.d.keys()

        def __str__(self):
            return "Note: %s" % self.d

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
        self.refList = []
        self.enabled = True

    def createNoteHolder(self):
        nh = NoteHolderGroup.NoteHolder(self)
        self.refList.append(weakref.ref(nh))
        return nh

    def strengthenRefs(self):
        self.refList = [strongRef(ref) for ref in self.refList]

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
        self.enabled = True

    def disableAll(self):
        self.enabled = False

    def writeNotesToResultsEntry(self, shdNet, results):
        raise RuntimeError('%s does not implement writeNotesToResultsEntry' % __name__)

    def writeNotesAsCSV(self, fnameOrFile, fields=None, requiredFields=None,
                        overrideFields=None, filterFunc=None, insertRows=None,
                        fileOpenFunc=None):
        """
        By default, create the named csv file and write all NoteHolder contents to it.

        If fields is specified, only output those columns.
        If requiredFields is specified, a row must have a value for that field
            for that row to be output (note that that column doesn't need to be
            a part of the output fields).
        if overrideFields is specified, a note with any field in overrideFields
            will be displayed regardless of "requiredFields"
        insertRows is a list of rows to be inserted at the top of the file.
            Each row should be a list of values to be inserted.
        if filterFunc is specified, it must be a function to filter the lists of
            CSV keys and records, with the signature:

               filteredKeyList, filteredRecDictList = filterFunc(keyList, recDictList)

            The filter is applied immediately before the CSV file is written, after all
            other argument processing has occurred.
        if fileOpenFunc is specified, it must be a substitute for the normal file open
            function, with signature:

              fileObject = fileOpenFunc(name, mode)

            If fnameOrFile is a string, fileOpenFunc will be called with mode='w' to
            open the file for writing.
        """

        requiredFields = listify(requiredFields, keepNone=True)
        overrideFields = listify(overrideFields)
        keyList = listify(fields)
        insertRows = listify(insertRows)

        fmtdInsertRows = []
        for row in insertRows:
            fmtd = ""
            for i, val in enumerate(row):
                if i > 0:
                    fmtd += ','
                fmtd += str(val)
            fmtd += '\n'
            fmtdInsertRows.append(fmtd)

        recDictList = []

        for n in [nRef() for nRef in self.refList if nRef() is not None]:
            if requiredFields is not None:
                if not reduce(lambda keep, field: keep or (field in n.d.keys()),
                              overrideFields,
                              False):
                    if not reduce(lambda keep, field: keep and (field in n.d.keys()),
                                  requiredFields,
                                  True):
                        continue
            if fields is None:
                for k in n.d.keys():
                    if k not in keyList:
                        keyList.append(k)
            recDictList.append(n.d)

        if fields is None:
            keyList.sort()
            if 'code' in keyList:
                keyList.remove('code')
            if 'name' in keyList:
                keyList.remove('name')
            keyList = ['code', 'name'] + keyList

        if filterFunc is not None:
            keyList, recDictList = filterFunc(keyList, recDictList)

        if fileOpenFunc is None:
            fileOpenFunc = open
        if isinstance(fnameOrFile, types.StringType):
            with fileOpenFunc(fnameOrFile, "w") as f:
                for fmtdRow in fmtdInsertRows:
                    f.write(fmtdRow)
                csv_tools.writeCSV(f, keyList, recDictList)
        else:
            for fmtdRow in fmtdInsertRows:
                f.write(fmtdRow)
            csv_tools.writeCSV(fnameOrFile, keyList, recDictList)

    def clearAll(self, keepRegex):
        """
        Clear all keys not matching keepRegex from all NoteHolders in this group.
        keepRegex can be either a regular expression object (from the 're' package)
        or a string that can be compiled into a regular expression object.
        """
        if isinstance(keepRegex, types.StringType):
            keepRegex = re.compile(keepRegex)
        for n in [nRef() for nRef in self.refList if nRef() is not None]:
            for k in n.d.keys():
                if not keepRegex.match(k):
                    del n.d[k]

    def printAll(self, printRegex='.*'):
        """
        Print all keys matching printRegex from all NoteHolders in this group.
        printRegex can be either a regular expression object (from the 're' package)
        or a string that can be compiled into a regular expression object.
        """
        if isinstance(printRegex, types.StringType):
            printRegex = re.compile(printRegex)
        for n in [nRef() for nRef in self.refList if nRef() is not None]:
            tmpD = {}
            for k, v in n.d.items():
                if printRegex.match(k):
                    tmpD[k] = v
            print(tmpD)

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

nested_pickle(NoteHolderGroup)
