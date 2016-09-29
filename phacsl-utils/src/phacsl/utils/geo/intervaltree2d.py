

class IT2DNode:
    def __init__(self, xMin, xMax, yMin, yMax, data):
        self.xMin = xMin
        self.xMax = xMax
        self.xHigh = xMax

        self.yMin = yMin
        self.yMax = yMax
        self.yHigh = yMax

        self.data = data

        self.branches = [None, None, None, None]
        # since there's no efficient means of removing things from a two dimensional tree it's easiest to
        # just mark the node as removed and later compact the tree
        self.removed = False


    def insert(self, node):
        "insert a node into the tree"
        branch = 0
        if node.xMin > self.xMin:
            branch = 1
        if node.yMin > self.yMin:
            branch += 2

        if self.branches[branch] is None:
            self.branches[branch] = node
            xHigh = node.xHigh
            yHigh = node.yHigh
        else:
            xHigh, yHigh = self.branches[branch].insert(node)

        if self.xHigh < xHigh:
            self.xHigh = xHigh
        if self.yHigh < yHigh:
            self.yHigh = yHigh
            
        return self.xHigh, self.yHigh


    def findNode(self, xMin, xMax, yMin, yMax, data):
        "find the node associated with a previously returned data blob"
        if data is self.data:
            return self
        branch = 0
        #print "xMin: %s, cur_xMin: %s, yMin: %s, cur_yMin: %s"%(xMin, self.xMin, yMin, self.yMin)
        if xMin > self.xMin:
            branch = 1
        if yMin > self.yMin:
            branch += 2
        return self.branches[branch].findNode(xMin, xMax, yMin, yMax, data)


    def remove(self, dNode):
        "remove dNode from the tree"
        dNode.removed = True


    def findIntersectPoint(self, x, y, results = None):
        return self.findIntersectSegmentPair(x, x, y, y, results)


    def findIntersectSegmentPair(self, xMin, xMax, yMin, yMax, results = None):
        if results is None:
            results = []

        if xMin > self.xHigh:
            return results
        if yMin > self.yHigh:
            return results


        # branches are the 4 branches + self as the 5th element
        if xMax < self.xMin:
            tryBranch = [True, False, True, False, False]
        else:
            tryBranch = [True, True, True, True, True]

        if yMax < self.yMin:
            tryBranch[2] = tryBranch[3] = tryBranch[4] = False

        for i in xrange(4):
            if tryBranch[i]:
                if self.branches[i] is not None:
                    self.branches[i].findIntersectSegmentPair(xMin, xMax, yMin, yMax, results)

        if tryBranch[4]:
            if xMin <= self.xMax and yMin <= self.yMax and self.removed is False:
                results.append(self.data)

        return results

    def intersectSegmentPairExists(self, xMin, xMax, yMin, yMax):
        if xMin > self.xHigh:
            return False
        if yMin > self.yHigh:
            return False


        # branches are the 4 branches + self as the 5th element
        if xMax < self.xMin:
            tryBranch = [True, False, True, False, False]
        else:
            tryBranch = [True, True, True, True, True]

        if yMax < self.yMin:
            tryBranch[2] = tryBranch[3] = tryBranch[4] = False

        if tryBranch[4]:
            if xMin <= self.xMax and yMin <= self.yMax and self.removed is False:
                return True

        for i in xrange(4):
            if tryBranch[i]:
                if self.branches[i] is not None:
                    if self.branches[i].findIntersectSegmentPair(xMin, xMax, yMin, yMax):
                        return True

        return False

        

    def all(self):
        if self.removed is True:
            results = []
        else:
            results = [self.data]
        for branch in self.branches:
            if branch is not None:
                results.extend(branch.all())
        return results

    def allNodes(self):
        results = [self]
        for branch in self.branches:
            if branch is not None:
                results.extend(branch.allNodes())
        return results



class IT2D:
    def __init__(self):
        self.rootNode = None

    def insert(self, node):
        if self.rootNode is None:
            self.rootNode = node
            return
        self.rootNode.insert(node)

    def allNodes(self):
        if self.rootNode is None:
            return []
        return self.rootNode.allNodes()
    
    def findNode(self, xMin, xMax, yMin, yMax, data):
        return self.rootNode.findNode(xMin, xMax, yMin, yMax, data)
            
    def findIntersectPoint(self, x, y):
        if self.rootNode is None:
            return []
        return self.rootNode.findIntersectSegmentPair(x, x, y, y)

    def findIntersectSegmentPair(self, xMin, xMax, yMin, yMax):
        if self.rootNode is None:
            return []
        return self.rootNode.findIntersectSegmentPair(xMin, xMax, yMin, yMax)

    def intersectSegmentPairExists(self, xMin, xMax, yMin, yMax):
        if self.rootNode is None:
            return False
        return self.rootNode.intersectSegmentPairExists(xMin, xMax, yMin, yMax)
    
    def remove(self, node):
        self.rootNode.remove(node)

    def all(self):
        if self.rootNode is None:
            return []
        return self.rootNode.all()

def testFindNode(tree, pTuple):
    xMin, xMax, yMin, yMax = pTuple
    print tree.findNode(xMin, xMax, yMin, yMax, pTuple).data
    
    
def main():
    t =      IT2DNode(1,5,7,9, (1,5,7,9))
    t.insert(IT2DNode(6,9,3,6, (6,9,3,6)))
    t.insert(IT2DNode(3,6,4,7, (3,6,4,7)))
    t.insert(IT2DNode(8,9,5,6, (8,9,5,6)))
    nnode = IT2DNode(4,7,3,8, (4,7,3,8))
    t.insert(nnode)
    t.insert(IT2DNode(2,8,5,7, (2,8,5,7)))
    t.insert(IT2DNode(1,3,2,4, (1,3,2,4)))
    t.insert(IT2DNode(3,7,2,4, (3,7,2,4)))
    t.insert(IT2DNode(6,8,1,5, (6,8,1,5)))
    t.insert(IT2DNode(4,8,8,9, (4,8,8,9)))
    t.insert(IT2DNode(1,9,1,9, (1,9,1,9)))

    
    print "2,4: %s"%t.findIntersectPoint(2,4)
    print "4,7: %s"%t.findIntersectPoint(4,7)
    print "1,3: %s"%t.findIntersectPoint(1,3)

    print "(2,4), (5,8): %s"%t.findIntersectSegmentPair(2,4,5,8)

    for pt in t.findIntersectSegmentPair(2,4,5,8):
        testFindNode(t, pt)

    print "all: %s"%t.all()
    
    print "removing %s"%(nnode.data,)
    t = t.remove(nnode)
    
    print "2,4: %s"%t.findIntersectPoint(2,4)
    print "4,7: %s"%t.findIntersectPoint(4,7)
    print "1,3: %s"%t.findIntersectPoint(1,3)

    print "(2,4), (5,8): %s"%t.findIntersectSegmentPair(2,4,5,8)
    for pt in t.findIntersectSegmentPair(2,4,5,8):
        testFindNode(t, pt)
    
    print "all: %s"%t.all()
    
if __name__ == "__main__":
    main()




