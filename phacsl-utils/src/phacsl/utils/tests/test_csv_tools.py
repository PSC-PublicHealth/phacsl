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

import phacsl.utils.formats.csv_tools as csv_tools


def main():
    "This is a simple test routine which takes csv files as arguments"
    global verbose, debug

    argList = []

    for a in sys.argv[1:]:
        if a == '-v':
            csv_tools.verbose = True
        elif a == '-d':
            csv_tools.debug = True
        else:
            argList.append(a)

    if argList:
        for a in argList:
            print(("##### Checking %s" % a))
            with open(a, "rU") as f:
                keys, recs = csv_tools.parseCSV(f)
            with open('test_csv_tools.csv', 'w') as f:
                csv_tools.writeCSV(f, keys, recs, quoteStrings=True)
            with open('test_csv_tools.csv', 'rU') as f:
                keys2, recs2 = csv_tools.parseCSV(f)
            assert(keys2 == keys)
            for i, tpl in enumerate(zip(recs2, recs)):
                r2, r = tpl
                if r != r2:
                    print(("##### record %d differs: " % i))
                    for k in keys:
                        if r[k] != r2[k]:
                            print(("%s:%s --> %s:%s" % (k, r[k], k, r2[k])))
            assert(recs2 == recs)
    else:
        print("No input files to check")

############
# Main hook
############

if __name__ == "__main__":
    main()
