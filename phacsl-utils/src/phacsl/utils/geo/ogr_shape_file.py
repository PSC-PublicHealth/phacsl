# this attempts to read the output from ogrinfo -al
# ie $ ogrinfo -al MOZ_adm2.shp > MOZ2.ogrinfo
#    $ cat MOZ2.ogrinfo

from phacsl.utils.misc.util import ReadFile

from glob import glob
import os.path

class OgrShapeFile:
    class EOF(Exception):
        pass
    
    def getLine(self):
        if self.nextLine is not None:
            self.curLine = self.nextLine
            self.nextLine = None
            self.lineNum += 1
            return self.curLine.strip()

        self.curLine = self.fh.readline()
        if self.curLine == '':
            raise self.EOF()
        self.lineNum += 1
        return self.curLine.strip()

    def pushLine(self):
        if self.nextLine is not None:
            raise RuntimeError("Can't push back more than one line")
        self.nextLine = self.curLine
        self.lineNum -= 1

    def __init__(self, fh):
        self.fh = fh
        self.lineNum = 0
        self.nextLine = None  # simple pushback buffer

        self.readHeader()

    
    def readHeader(self):
        # I'm not sure that there's anything in the header that I really want.  Currently
        # I'm just going to burn through it and point myself at the first feature.

        try:
            while(True):
                line = self.getLine()
                if line.startswith('OGRFeature'):
                    self.pushLine()
                    return
        except:
            raise RuntimeError("failed to find start of first feature in shape file")

    def getFeature(self, discardInnerRings = True):
        """
        get a feature from the ogrinfo shape file.
        returns an tuple of:
            an attribute dict
            if discardInnerRings is set 
                a list of polygons
            else
                a list of lists of polygons.
        """

        while True:
            try:
                line = self.getLine()
            except:
                # if here, we've hit the file end at a reasonable break
                return None, None

            if len(line) == 0:
                continue
            if line.startswith('OGRFeature'):
                break
            # Ran into something unexpected
            raise RuntimeError('unexpected data on line %d of shape file'%self.lineNume)

        featureStartLine = self.lineNum

        lines = []
        while True:
            try:
                line = self.getLine()
            except:
                break
            if line.startswith('OGRFeature'):
                self.pushLine()
                break
            lines.append(line)
            #print line[:20]

        attributes = {}
        plines = []
        mlines = []
        
        polygons = []
        for line in lines:
            if line.startswith('POLYGON'):
                plines.append(line)
            if line.startswith('MULTIPOLYGON'):
                mlines.append(line)

            try:
                key,val = line.split('=')
                try:
                    key,xxx = key.split('(')
                except:
                    pass
                key = key.strip()
                val = val.strip()
                attributes[key] = val
            except:
                pass
        if len(mlines) + len(plines) != 1:
            raise RuntimeError('should be exactly one polygon/multipolygon line in feature starting on line %d'%featureStartLine)
        if len(plines) == 1:
            #print plines[0]
            blank,key,pstring = plines[0].partition('POLYGON ((')
        if len(mlines) == 1:
            #print plines[0]
            blank,key,pstring = mlines[0].partition('MULTIPOLYGON (((')
        pstring = pstring.rstrip(')')

        #print pstring
        if discardInnerRings:
            pstrings = pstring.split(')),((')
            for s in pstrings:
                sllpairs = s.split(',')
                llpairs = []
                innerRing = False
                for sll in sllpairs:
                    #print sll
                    x,y = sll.split()
                    if y.endswith(')'):
                        print "discarding inner ring!"
                        #print s
                        #print sllpairs
                        innerRing = True
                        y = y.rstrip(')')
                    llpairs.append([float(x), float(y)])
                    if innerRing:
                        break

                polygons.append(llpairs)

        else:
            pstrings = pstring.split(')),((')
            for s in pstrings:
                sllpairs = s.split(',')
                llpairs = []
                ringList = []

                for sll in sllpairs:
                    #print sll
                    x,y = sll.split()
                    if x.startswith('('):
                        x = x.strip('(')
                        ringList.append(llpairs)
                    if y.endswith(')'):
                        #print "inner ring!"
                        y = y.rstrip(')')
                    llpairs.append([float(x), float(y)])
                ringList.append(llpairs)

                polygons.append(ringList)
            
        return attributes, polygons


def readShapeFile(filename, discardInnerRings=True):
    shapes = []
    
    with ReadFile(filename) as f:
        sf = OgrShapeFile(f)

        while(True):
            attr, poly = sf.getFeature(discardInnerRings)
            if attr is None:
                break

            shapes.append((attr, poly))
            
    return shapes
            
