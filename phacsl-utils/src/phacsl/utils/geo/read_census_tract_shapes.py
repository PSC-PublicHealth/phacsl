import httplib
import os.path
import gzip
import bz2

from sh import ogrinfo, unzip

from subprocess import call
from tempfile import mkdtemp
from shutil import rmtree
from glob import glob


import ogr_shape_file as sf
from polygon_calcs import *
import pointinpolygon as piPoly

from collections import namedtuple
import intervaltree2d

NotStateFipsCodes = set([3,7,14,43,52])  # reserved codes that were never used
# all of the US state FIPS codes (including DC) and also get puerto rico (72) because this is what we have shape files for
StateFipsCodes = [x for x in filter(lambda y: y not in NotStateFipsCodes, xrange(1,57))] + [72]

cTract = namedtuple('cTract', ['sId', 'cTractPolygons', 'extent', 'centroid'])
cTractPoly = namedtuple('cTractPoly', ['sId', 'extent', 'polygon', 'innerRings', 'pHandle', 'irHandles', 'centroid'])

class CensusTractShapesBase:
    def __init__(self, rootDir='shapefile_cache', includeStates = None):
        self.shapeFileDir = os.path.join(rootDir, 'census_tract_shapes/%s/'%self.year)
        if not os.path.exists(self.shapeFileDir):
            os.makedirs(self.shapeFileDir)
        self.getCensusTractShapes(includeStates)

    def ogrFileName(self, fipsCode):
        return os.path.join(self.shapeFileDir, "censusTracts_%02d.ogrinfo.gz"%fipsCode)

    def downloadShapeFile(self, fipsCode):
        print(("downloading %s"%fipsCode))
        sFile = self.netShapeFile.replace('XX', "%02d"%fipsCode)
        path = self.netShapePath + sFile
        conn = httplib.HTTPConnection(self.netShapeHost)
        conn.request("GET", path)
        r = conn.getresponse()

        if r.status != 200:
            raise RuntimeError("*** failed download ***\n\t%s, %s, %s"% (sFile, r.status, r.reason))

        tmpDir = mkdtemp()
        sFileFull = os.path.join(tmpDir, sFile)
        with open(sFileFull, "wb") as f:
            data = r.read()
            f.write(data)

        conn.close()

        unzip(sFileFull, d=tmpDir)
        shapeFiles = glob(os.path.join(tmpDir, '*.shp'))
        if len(shapeFiles) != 1:
            raise RuntimeError("There should only be one shape file in %s, failing"%sFile)
        for shapeFile in shapeFiles:
            infoName = self.ogrFileName(fipsCode)
            with gzip.open(infoName, "wb") as f:
                ogrinfo('-al', shapeFile, _out=f)
        rmtree(tmpDir)

    def getCensusTractShapes(self, includeStates):
        cTractTree = intervaltree2d.IT2D()
        tractDict = {}

        stateList = StateFipsCodes
        if includeStates is not None:
            stateList = includeStates
        for sfc in stateList:
            fn = self.ogrFileName(sfc)
            if not os.path.isfile(fn):
                self.downloadShapeFile(sfc)

            sdata = sf.readShapeFile(fn, discardInnerRings=False)

            for attrs,shape in sdata:
                #print attrs
                sId = self.tractIdFn(attrs)
                cTractPolygons = []
                outerCAList = []
                
                for polyList in shape:
                    poly = polyList[0]  # get primary polygon
                    if poly[0] != poly[-1]:
                        poly = tuple(poly[:])+(poly[0],)
                    polygon = poly

                    extent = polygonExtent(poly)
                    minLon, minLat, maxLon, maxLat = extent
                    pHandle = piPoly.PointInPolygon(poly)

                    caList = [centroidArea(polygon)]
                    
                    
                    # process the inner rings
                    innerRingHandles = []
                    innerRings = []
                    for poly in polyList[1:]:
                        if poly[0] != poly[-1]:
                            poly = tuple(poly[:])+(poly[0],)
                        innerRings.append(poly)
                        innerRingHandles.append(piPoly.PointInPolygon(poly))
                        ca = centroidArea(poly)
                        caList.append((ca[0], ca[1], -ca[2]))
                    cx, cy, area = multiCentroidArea(caList)

                    # some census tracts are strictly bodies of water where the outer ring encloses an identical
                    # inner ring.
                    if area == 0.0:
                        cx,cy,area = caList[0]
                    outerCAList.append((cx, cy, area))
                    #print cx, cy, area
                    centroid = (cx,cy)


                    fullPoly = cTractPoly(sId, extent, polygon, innerRings, pHandle, innerRingHandles, centroid)
                    cTractPolygons.append(fullPoly)
                    node = intervaltree2d.IT2DNode(minLon, maxLon, minLat, maxLat, fullPoly)
                    cTractTree.insert(node)

                cx, cy, area = multiCentroidArea(outerCAList)
                extent = multiExtent([p.extent for p in cTractPolygons])
                tractDict[sId] = cTract(sId, cTractPolygons, extent, (cx, cy))

        self.tracts = tractDict
        self.tree = cTractTree

    def findTract(self, lon, lat, ignoreInnerRings = False, allowedInInnerRings = False):
        """
        find a census tract based on lon, lat.
        * ignore inner subtracted rings (and return anything within the outer ring) if 
          ignoreInnerRings is set.
        * return results that fall in subtracted inner rings if there are no other results if 
          allowedInInnerRings is set.
        """
        ret = []
        innerFailed = []
        tracts = self.tree.findIntersectPoint(lon, lat)

        for tract in tracts:
            if tract.pHandle.inPolygon((lon, lat)):
                if ignoreInnerRings:
                    ret.append(tract)
                    continue
                
                innerOk = True
                for handle in tract.irHandles:
                    if handle.inPolygon((lon, lat)):
                        innerOk = False
                        break
                if innerOk:
                    ret.append(tract)
                else:
                    innerFailed.append(tract)
        if not allowedInInnerRings:
            return ret
        if len(ret) == 0:
            return innerFailed
        return ret

class CensusTractShapes1990(CensusTractShapesBase):
    def __init__(self, rootDir='shapefile_cache', includeStates=None):
        self.year = 1990
        self.netShapeHost = 'www2.census.gov'
        self.netShapePath = '/geo/tiger/PREVGENZ/tr/tr90shp/'
        self.netShapeFile = 'trXX_d90_shp.zip'
        CensusTractShapesBase.__init__(self, rootDir, includeStates)

    def tractIdFn(self, attrs):
        try:
            tn = float(attrs['TRACT_NAME'])
            ftn = "%04.2f"%tn
        except:
            # there are two tracts that have '(null)' attributes and fail all of this
            print(("Can't convert tract name %s"%attrs['TRACT_NAME']))
            print(attrs)
            ftn = attrs['TRACT_NAME']
        return attrs['ST'] + attrs['CO'] + attrs['TRACTBASE'] + ftn

class CensusTractShapes2000(CensusTractShapesBase):
    def __init__(self, rootDir='shapefile_cache', includeStates=None):
        self.year = 2000
        self.netShapeHost = 'www2.census.gov'
        self.netShapePath = '/geo/tiger/PREVGENZ/tr/tr00shp/'
        self.netShapeFile = 'trXX_d00_shp.zip'
        CensusTractShapesBase.__init__(self, rootDir, includeStates)

    def tractIdFn(self, attrs):
        return attrs['STATE'] + attrs['COUNTY'] + attrs['TRACT']

class CensusTractShapes2010(CensusTractShapesBase):
    def __init__(self, rootDir='shapefile_cache', includeStates=None):
        self.year = 2010
        self.netShapeHost = 'www2.census.gov'
        self.netShapePath = '/geo/tiger/GENZ2010/'
        self.netShapeFile = 'gz_2010_XX_140_00_500k.zip'
        CensusTractShapesBase.__init__(self, rootDir, includeStates)

    def tractIdFn(self, attrs):
        #print attrs
        #raise RuntimeError("just stop")
        return attrs['STATE'] + attrs['COUNTY'] + attrs['TRACT']

class CensusTractShapes2013(CensusTractShapesBase):
    def __init__(self, rootDir='shapefile_cache', includeStates=None):
        self.year = 2013
        self.netShapeHost = 'www2.census.gov'
        self.netShapePath = '/geo/tiger/GENZ2013/'
        self.netShapeFile = 'cb_2013_XX_tract_500k.zip'
        CensusTractShapesBase.__init__(self, rootDir, includeStates)

    def tractIdFn(self, attrs):
        return attrs['GEOID']

class CensusTractShapes2014(CensusTractShapesBase):
    def __init__(self, rootDir='shapefile_cache', includeStates=None):
        self.year = 2014
        self.netShapeHost = 'www2.census.gov'
        self.netShapePath = '/geo/tiger/GENZ2014/shp/'
        self.netShapeFile = 'cb_2014_XX_tract_500k.zip'
        CensusTractShapesBase.__init__(self, rootDir, includeStates)

    def tractIdFn(self, attrs):
        return attrs['GEOID']

class CensusTractShapes2015(CensusTractShapesBase):
    def __init__(self, rootDir='shapefile_cache', includeStates=None):
        self.year = 2015
        self.netShapeHost = 'www2.census.gov'
        self.netShapePath = '/geo/tiger/GENZ2015/shp/'
        self.netShapeFile = 'cb_2015_XX_tract_500k.zip'
        CensusTractShapesBase.__init__(self, rootDir, includeStates)

    def tractIdFn(self, attrs):
        return attrs['GEOID']

