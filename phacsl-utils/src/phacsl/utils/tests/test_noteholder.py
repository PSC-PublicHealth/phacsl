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

import sys
import StringIO
import unittest

from phacsl.utils.notes.noteholder import NoteHolderGroup


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

    if len(myargv) < 2:
        describeSelf()
    elif myargv[1] == 'testnote':
        nhg1 = NoteHolderGroup()
        nhg2 = NoteHolderGroup()
        if len(myargv) == 2:
            print "---- creating groups of NoteHolders ----"
            nh1_1 = nhg1.createNoteHolder()
            nh1_1.addNote({"int": 0, "float": 1.0, "word": "hello "})
            print 'nh1_1: '+str(nh1_1)
            nh1_2 = nhg1.createNoteHolder()
            nh1_2.addNote({"float": 1234.5, "word": "foobar"})
            print 'nh1_2: ' + str(nh1_2)
            print "---- testing addNote ----"
            for i in xrange(10):
                nh1_1.addNote({"int": i, "float": (1.0+0.1*i), "word": "world "})
            print 'nh1_1: ' + str(nh1_1)
            nh2_1 = nhg2.createNoteHolder()
            nh2_1.addNote({"float": 13243.5, "word": "Iamnh2_1"})
            nh1_1.addNote({"float": 6789.0, "word": "foobar"})
            print "---- generating CSV; fake file contents follow ----"
            stringFile = StringIO.StringIO()
            stringFile.encoding = 'ascii'  # covers a weakness of StringIO
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
            for n in [nh1_1, nh1_2, nh2_1]:
                n.addNote({"test": "ngh1only"})
            nhg1.disableAll()
            nhg2.enableAll()
            for n in [nh1_1, nh1_2, nh2_1]:
                n.addNote({"test": "ngh2only"})
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
        for a, b in zip(readBack.readlines(), correctRecs.readlines()):
            # print "<%s> vs. <%s>"%(a,b)
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
        readBack = self.getReadBackBuf(['dummy', 'testnote'])
        self.compareOutputs(correctStr, readBack)


############
# Main hook
############

if __name__ == "__main__":
    main()
