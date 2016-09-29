import math as m


# utility functions for epsg3857 projections

def radToY(rad):
    y = m.log(m.tan(m.pi/4 + rad/2))
    return y

def yToRad(y):
    rad = (2 * m.atan(m.exp(y)) - m.pi/2)
    return rad

def degToRad(deg):
    return deg / 180.0 * m.pi

def radToDeg(rad):
    return rad / m.pi * 180.0

def degToY(deg):
    return radToY(degToRad(deg))

def yToDeg(y):
    return radToDeg(yToRad(y))


class epsg3857():
    def __init__(self, extent, resolution):
        """
        extent is a tuple of the form: (minLon, minLat, maxLon, maxLat) in decimal degrees.
        resolution is number of pixels in the form (x,y) (or (lon,lat)).
    
        """
        self.minLon, self.minLat, self.maxLon, self.maxLat = extent
        # resolution needs to be a tuple of integers
        resolution = (int(round(resolution[0])), int(round(resolution[1])))
        self.res = resolution
        self.lonRes, self.latRes = resolution
        self.lonInc = (self.maxLon - self.minLon) / self.lonRes
        #self.latInc = (self.maxLat - self.minLat) / self.latRes
        self.baseYMin = degToY(self.minLat)
        self.baseYMax = degToY(self.maxLat)
        self.baseYDiff = self.baseYMax - self.baseYMin
        self.baseYInc = self.baseYDiff / self.latRes
        self.pixelLat = [] #np.zeros((self.latRes+1), dtype=np.float_)
        baseY = self.baseYMin
        for y in xrange(self.latRes+1):
            self.pixelLat.append(yToDeg(baseY))
            # self.pixelLat[y] = yToDeg(baseY)
            baseY += self.baseYInc

    def whichPixel(self, lon, lat):
        x = (lon - self.minLon) / self.lonInc
        if x < 0.0:
            x -= 1.0
        x = int(x)

        baseY = degToY(lat) - self.baseYMin
        y = baseY / self.baseYInc
        if y < 0.0:
            y -= 1.0
        y = self.res[1] - int(y) - 1
        return x,y

    def pixelToDegClean(self, x, y):
        """
        assumes we're using integer x,y that are within the image bounds
        """
        lon = self.minLon + x * self.lonInc
        lat = self.pixelLat[self.res[1] - 1 - y]
        return lon,lat
        
        
    def pixelToDeg(self, x, y):
        lon = self.minLon + x * self.lonInc
        lat = yToDeg(self.baseYMin + (self.res[1] - 1 - y) * self.baseYInc)
        return lon, lat
