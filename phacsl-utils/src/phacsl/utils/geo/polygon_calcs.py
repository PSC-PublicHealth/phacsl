# for all of the following
# extentList is (minX, minY, maxX, maxY) or (minLon, minLat, maxLon, maxLat)

def polygonExtent(polygon, extentList = None):
    """
    given points on a polygon (in the form [[x,y],[x,y],[x,y]...])
    return min x, min y, max x, max y
    """

    if extentList is None:
        minX = maxX = polygon[0][0]
        minY = maxY = polygon[0][1]
    else:
        (minX, minY, maxX, maxY) = extentList
    for x,y in polygon:
        if x < minX:
            minX = x
        elif x > maxX:
            maxX = x
        if y < minY:
            minY = y
        elif y > maxY:
            maxY = y

    return minX, minY, maxX, maxY

def multiPolygonExtent(polygonList, extentList = None):
    for polygon in polygonList:
        extentList = polygonExtent(polygon, extentList)
    return extentList

def multiExtent(extentList):
    minXList, minYList, maxXList, maxYList = zip(*extentList)
    return min(minXList), min(minYList), max(maxXList), max(maxYList)
    

def signedArea(polygon):
    a = 0.0
    for p1, p2 in zip(polygon[:-1], polygon[1:]):
        a += p1[0]*p2[1] - p2[0]*p1[1]
    return 0.5 * a

def area(polygon):
    return abs(signedArea(polygon))

def centroidArea(polygon):
    """
    return the centroid and a positive area for a polygon in the form x,y,a
    """
    a2 = 0.0   # this is double the signed area 
    cx = 0.0
    cy = 0.0

    for p1, p2 in zip(polygon[:-1], polygon[1:]):
        x1, y1 = p1
        x2, y2 = p2
        det = (x1*y2 - x2*y1)
        a2 += det
        cx += (x1 + x2) * det
        cy += (y1 + y2) * det

    a6 = a2 * 3.0  # 6 x signed area
    cx /= a6
    cy /= a6

    return cx,cy,abs(a2/2.0)

def centroid(polygon):
    x,y,a = centroidArea(polygon)
    return x,y

def multiCentroidArea(centroidAreaList):
    """
    take a list of centroids/areas in the form (x,y,a) as created by CentroidArea()
    and calculate the centroid and area for all of the objects as a single object
    if a is negative, treat it as a hole.
    """ 

    area = 0.0
    cxn = 0.0  # centroid x numerator
    cyn = 0.0  # centroid y numerator
    for x,y,a in centroidAreaList:
        area += a
        cxn += x * a
        cyn += y * a

    if area == 0.0:
        return 0.0, 0.0, 0.0
    return cxn / area, cyn / area, area
        

    
    
