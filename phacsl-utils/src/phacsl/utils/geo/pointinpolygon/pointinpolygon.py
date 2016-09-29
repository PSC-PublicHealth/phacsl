import numpy as np
import cext as pipc

class PointInPolygon:
    """ determines if a point is in a polygon
    takes an initial polygon and turns it into an interval tree
    so that point in polygon operations are very quick
    """

    def __init__(self, polygon):
        dtype = [('x0', 'f8'), ('y0', 'f8'), # lower point
                 ('x1', 'f8'), ('y1', 'f8'), # higher point
                 ('yHigh', 'f8'),            # y value of highest point on branch of tree
                 ('l0', 'i8'), ('l1', 'i8'), # indices of next branches
                 ('wnInc', 'i8')] # 1 if in normal order, -1 if points reversed
        self.polygon = np.zeros((len(polygon) - 1,), dtype)
        for i, (p0, p1) in enumerate(zip(polygon[:-1], polygon[1:])):
            if p0[1] < p1[1]:
                self.polygon[i] = (p0[0], p0[1], p1[0], p1[1], p1[1], -1, -1, 1)
            else:
                self.polygon[i] = (p1[0], p1[1], p0[0], p0[1], p0[1], -1, -1, -1)
                

        # get things out of order so the tree is more likely to be balanced
        np.random.shuffle(self.polygon)
        
        # convert the list to an interval tree
        if 0:
            for i in xrange(1, len(self.polygon)): # index to be inserted
                iNode = self.polygon[i]
                yHigh = iNode['yHigh']
                c = 0                               # root index
                while True:
                    cNode = self.polygon[c]

                    if yHigh > cNode['yHigh']:
                        cNode['yHigh'] = yHigh

                    branch = 'l0'
                    if iNode['y0'] > cNode['y0']:
                        branch = 'l1'
                    if cNode[branch] == -1:
                        cNode[branch] = i
                        break
                    c = cNode[branch]
        else:
            pipc.buildTree(self.polygon)

        #print self.polygon
        
    def wn(self, x, y, c):
        cNode = self.polygon[c]
        if y > cNode['yHigh']:
            return 0
        
        if cNode['l0'] != -1:
            n = self.wn(x, y, cNode['l0'])
        else:
            n = 0

        if y >= cNode['y0']:
            if cNode['l1'] != -1:
                n += self.wn(x, y, cNode['l1'])
            
            # see if this specific node works
            if y < cNode['y1']:
                isLeft = (cNode['x1'] - cNode['x0']) * (y - cNode['y0']) - (x - cNode['x0']) * (cNode['y1'] - cNode['y0'])
                if isLeft > 0.0:
                    n += cNode['wnInc']
                
        return n

    def inPolygon(self, p):
        ap = np.array(p)
        return pipc.inPolygon(ap, self.polygon)


        x,y = p
        
        if 0 == self.wn(x, y, 0):
            return 0
        return 1
    
class RectInPolygon:
    def __init__(self, polygon):
        dtype = [('x0', 'f8'), ('y0', 'f8'), # lower point
                 ('x1', 'f8'), ('y1', 'f8'), # higher point
                 ('yHigh', 'f8'),            # y value of highest point on branch of tree
                 ('l0', 'i8'), ('l1', 'i8'), # indices of next branches
                 ('wnInc', 'i8')] # 1 if in normal order, -1 if points reversed
        self.polygon = np.zeros((len(polygon) - 1,), dtype)
        for i, (p0, p1) in enumerate(zip(polygon[:-1], polygon[1:])):
            if p0[1] < p1[1]:
                self.polygon[i] = (p0[0], p0[1], p1[0], p1[1], p1[1], -1, -1, 1)
            else:
                self.polygon[i] = (p1[0], p1[1], p0[0], p0[1], p0[1], -1, -1, -1)
                

        # get things out of order so the tree is more likely to be balanced
        np.random.shuffle(self.polygon)

        # convert the list to an interval tree
        pipc.buildTree(self.polygon)

        # create invPolygon to swap the x and y
        self.invPolygon = np.zeros((len(polygon) - 1,), dtype)
        for i, (p0, p1) in enumerate(zip(polygon[:-1], polygon[1:])):
            if p0[0] < p1[0]:
                self.invPolygon[i] = (p0[1], p0[0], p1[1], p1[0], p1[0], -1, -1, 1)
            else:
                self.invPolygon[i] = (p1[1], p1[0], p0[1], p0[0], p0[0], -1, -1, -1)
                

        # get things out of order so the tree is more likely to be balanced
        np.random.shuffle(self.invPolygon)
        
        # convert the list to an interval tree
        pipc.buildTree(self.invPolygon)



    def inPolygon(self, p0, p1=None):
        if p1 is None:
            ap = np.array(p0)
            if pipc.inPolygon(ap, self.polygon):
                return 'I'
            else:
                return 'O'

        x0,y0 = p0
        x1,y1 = p1

        ap = np.zeros(3)

        ap[0:3] = [x0, y0, x1]
        if pipc.hlineIntersectsPoly(ap, self.polygon): return 'S'
        ap[1] = y1
        if pipc.hlineIntersectsPoly(ap, self.polygon): return 'S'

        ap[0:3] = [y0, x0, y1]
        if pipc.hlineIntersectsPoly(ap, self.invPolygon): return 'S'
        ap[1] = x1
        if pipc.hlineIntersectsPoly(ap, self.invPolygon): return 'S'

        ap = np.array((x0,y0))
        ap2 = np.array((x1,y1))
        if pipc.inPolygon(ap, self.polygon) and pipc.inPolygon(ap2, self.polygon):
            return 'I'
        return 'O'

