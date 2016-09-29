#include "Python.h"
#include "numpy/arrayobject.h"
#include <stdio.h>
using namespace std;


size_t memberOffset(PyArrayObject *npObject, const char *field) {
    PyArray_Descr *dtype = PyArray_DTYPE(npObject);
    PyObject *fields = dtype->fields;
    PyObject *defTuple = PyDict_GetItemString(fields, field);  // borrowed reference
    PyObject *offsetObject = PySequence_GetItem(defTuple, 1);  // new reference
    long offsetLong = PyInt_AsLong(offsetObject);
    Py_XDECREF(offsetObject);
    size_t offset = offsetLong;
    return offset;
}

inline double memberDouble(PyArrayObject *o, long row, size_t offset) {
    return *((double *)((char *)PyArray_GETPTR1(o, row) + offset));
}

inline int64_t memberLong(PyArrayObject *o, long row, size_t offset) {
    return *((int64_t *)((char *)PyArray_GETPTR1(o, row) + offset));
}

inline double memberDouble(void *rowPtr, size_t offset) {
    return *((double *)((char *)rowPtr + offset));
}

inline int64_t memberLong(void *rowPtr, size_t offset) {
    return *((int64_t *)((char *)rowPtr + offset));
}

inline double *memberDoublePtr(void *rowPtr, size_t offset) {
    return (double *)((char *)rowPtr + offset);
}

inline int64_t *memberLongPtr(void *rowPtr, size_t offset) {
    return (int64_t *)((char *)rowPtr + offset);
}


struct PGonInfo {
    PyArrayObject *polygon;
    // offsets
    size_t ox0, oy0, ox1, oy1, oyHigh, ol0, ol1, ownInc;
    double x, y;
    double x2;   // used for hlineInPoly
    
    void setOffsets(PyArrayObject *polygon_) {
	polygon = polygon_;
	ox0 = memberOffset(polygon, "x0");
	oy0 = memberOffset(polygon, "y0");
	ox1 = memberOffset(polygon, "x1");
	oy1 = memberOffset(polygon, "y1");
	oyHigh = memberOffset(polygon, "yHigh");
	ol0 = memberOffset(polygon, "l0");
	ol1 = memberOffset(polygon, "l1");
	ownInc = memberOffset(polygon, "wnInc");
    }

};

long wnPnPoly_it(PGonInfo &pgi, int row);


long wnPnPoly_it(PGonInfo &pgi, int row) {
    void *rowPtr = PyArray_GETPTR1(pgi.polygon, row);
    double yHigh = memberDouble(rowPtr, pgi.oyHigh);
    double y = pgi.y;
    if (y > yHigh)
	return 0;

    long n = 0;
    int64_t l0 = memberLong(rowPtr, pgi.ol0);
    if (l0 != -1)  // check left if applicable (always if we've gotten this far)
	n = wnPnPoly_it(pgi, l0);

    double y0 = memberDouble(rowPtr, pgi.oy0);
    if (y >= y0) {
	int64_t l1 = memberLong(rowPtr, pgi.ol1);
	if (l1 != -1)  // check right if applicable
	    n += wnPnPoly_it(pgi, l1);

	// check this specific row
	double y1 = memberDouble(rowPtr, pgi.oy1);
	if (y < y1) {
	    double x = pgi.x;
	    double x0 = memberDouble(rowPtr, pgi.ox0);
	    double x1 = memberDouble(rowPtr, pgi.ox1);
	    if (0.0  < ((x1 - x0) * (y - y0) - (x - x0) * (y1 - y0))) {
		int64_t wnInc = memberLong(rowPtr, pgi.ownInc);
		n += wnInc;
	    }
	}
    }

    return n;
}


static PyObject* inPolygon_it (PyObject *dummy, PyObject *args) {
    PyArrayObject *point = NULL;
    PyArrayObject *polygon = NULL;
    PGonInfo pgi;

    if (!PyArg_ParseTuple(args, "O!O!", 
			  &PyArray_Type, &point, &PyArray_Type, &polygon))
	return NULL;

    // verify dimensions first
    if (1 != PyArray_NDIM(point)) 
	return NULL;
    if (2 != point->dimensions[0])
	return NULL;
    
    pgi.x = *(double *)PyArray_GETPTR1(point, 0);
    pgi.y = *(double *)PyArray_GETPTR1(point, 1);
    
    if (1 != PyArray_NDIM(polygon)) 
	return 0;

    pgi.setOffsets(polygon);
 

    long wn = wnPnPoly_it(pgi, 0);
    if (0 == wn)
	return PyInt_FromLong(0);
    return PyInt_FromLong(1);
}


long doHlineIntersectsPoly(PGonInfo &pgi, int row) {
    void *rowPtr = PyArray_GETPTR1(pgi.polygon, row);
    double yHigh = memberDouble(rowPtr, pgi.oyHigh);
    double y = pgi.y;
    if (y > yHigh)
	return 0;

    int64_t l0 = memberLong(rowPtr, pgi.ol0);
    if (l0 != -1)  // check left if applicable (always if we've gotten this far)
	if (doHlineIntersectsPoly(pgi, l0))
	    return 1;

    double y0 = memberDouble(rowPtr, pgi.oy0);
    if (y >= y0) {
	int64_t l1 = memberLong(rowPtr, pgi.ol1);
	if (l1 != -1)  // check right if applicable
	    if (doHlineIntersectsPoly(pgi, l1))
		return 1;

	// check this specific row
	double y1 = memberDouble(rowPtr, pgi.oy1);
	if (y < y1) {  // this segment of the polygon crosses the same y as our hline
	    double x = pgi.x;
	    double x2 = pgi.x2;
	    double x0 = memberDouble(rowPtr, pgi.ox0);
	    double x1 = memberDouble(rowPtr, pgi.ox1);

	    double intercept = x1 - ((y1-y) / (y1-y0) * (x1-x0));
	    if ((x < intercept) && (x2 > intercept))
		return 1;
	}
    }
    
    return 0;

}

static PyObject* hlineIntersectsPoly (PyObject *dummy, PyObject *args) {
    PyArrayObject *point = NULL;
    PyArrayObject *polygon = NULL;
    PGonInfo pgi;

    if (!PyArg_ParseTuple(args, "O!O!", 
			  &PyArray_Type, &point, &PyArray_Type, &polygon))
	return NULL;

    // verify dimensions first
    if (1 != PyArray_NDIM(point)) 
	return NULL;
    if (3 != point->dimensions[0])
	return NULL;
    
    pgi.x = *(double *)PyArray_GETPTR1(point, 0);
    pgi.y = *(double *)PyArray_GETPTR1(point, 1);
    pgi.x2 = *(double *)PyArray_GETPTR1(point, 2);
    if (1 != PyArray_NDIM(polygon)) 
	return 0;

    pgi.setOffsets(polygon);
 

    long ret = doHlineIntersectsPoly(pgi, 0);
    return PyInt_FromLong(ret);
}


static PyObject* buildTree_it (PyObject *dummy, PyObject *args) {
    PyArrayObject *polygon = NULL;
    PGonInfo pgi;

    if (!PyArg_ParseTuple(args, "O!", &PyArray_Type, &polygon))
	return NULL;

    if (1 != PyArray_NDIM(polygon)) 
	return 0;
    long vertexCount = polygon->dimensions[0];

    pgi.setOffsets(polygon);
    
    for (long row = 1; row < vertexCount; ++row) {
	void *rowPtr = PyArray_GETPTR1(pgi.polygon, row);
	double yHigh = memberDouble(rowPtr, pgi.oyHigh);
	double y0 = memberDouble(rowPtr, pgi.oy0);

	long c = 0;

	while(1) {
	    void *cPtr = PyArray_GETPTR1(pgi.polygon, c);
	    double *c_yHigh = memberDoublePtr(cPtr, pgi.oyHigh);
	    if (yHigh > *c_yHigh)
		*c_yHigh = yHigh;

	    size_t branchOffset = pgi.ol0;
	    double c_y0 = memberDouble(cPtr, pgi.oy0);
	    if (y0 > c_y0)
		branchOffset = pgi.ol1;
	    int64_t *c_br = memberLongPtr(cPtr, branchOffset);
	    if (*c_br == -1) {
		*c_br = row;
		break;
	    }
	    c = *c_br;
	}
    }

    return PyInt_FromLong(0);
}


static struct PyMethodDef methods[] = {
    {"inPolygon", inPolygon_it, METH_VARARGS, "inPolygon using a numpy intervalTree"},
    {"buildTree", buildTree_it, METH_VARARGS, "build interval tree for inPolygon_it()"},
    {"hlineIntersectsPoly", hlineIntersectsPoly, METH_VARARGS, "see if an hline intersects a polygon"},
    {NULL, NULL, 0, NULL}
};

PyMODINIT_FUNC
initcext (void) { 
    (void)Py_InitModule("cext", methods);
    import_array();
}



#if 0
// I started writing this and then realized that this was a waste of time.  Keeping it 'til I know I can discard it.

char checkRect(PGonInfo &pgi, double x, double y, double xHigh, double yHigh, double xRes, double yRes) {
    // Check if an area is inside the polygon, outside the polygon or straddling the polygon
    // returns 'I', 'O', or 'S'
    // walks the edges or the rectangle at res intervals or smaller and determines status is all
    // points checked are in, out or both.

    double xSpan = xHigh - x;
    double ySpan = yHigh - y;

    // if the rectangle is smaller than res, just check the center and call it based on that
    if ((xSpan < pgi.xRes) && (ySpan < pgi.yRes)) {
	xCenter = xSpan / 2.0 + pgi.x;
	yCenter = ySpan / 2.0 + pgi.y;
	if (pgi.inPoly(xCenter, yCenter))
	    return 'I';
	return 'O';
    }

    // check the corners
    int base = pgi.inPoly(x, y);
    if base != pgi.inPoly(x    , yHigh) return 'S';
    if base != pgi.inPoly(xHigh, yHigh) return 'S';
    if base != pgi.inPoly(xHigh, y    ) return 'S';

    // check the edges
    long xFirstInc = xSpan / 2.0;
    while (xSpan > xRes) {
	double curX = x + xFirstInc;
	while (curX < xHigh) {
	    if (base != pgi.inPoly(curX, x    )) return 'S';
	    if (base != pgi.inPoly(curX, xHigh)) return 'S';
	    curX += xSpan;
	}
	xSpan = xFirstInc;
	xFirstInc /= 2.0;
    }
    
    long yFirstInc = ySpan / 2.0;
    while (ySpan > yRes) {
	double curY = y + yFirstInc;
	while (curY < yHigh) {
	    if (base != pgi.inPoly(x    , curY)) return 'S';
	    if (base != pgi.inPoly(xHigh, curY)) return 'S';
	    curX += xSpan;
	}
	ySpan = yFirstInc;
	yFirstInc /= 2.0;
    }

    if (base)
	return 'I';
    return 'O';
}
    
static PyObject* rectInPolygon (PyObject *dummy, PyObject *args) {
    PyArrayObject *rect = NULL;
    PyArrayObject *polygon = NULL;
    PGonInfo pgi;

    if (!PyArg_ParseTuple(args, "O!O!", 
			  &PyArray_Type, &rect, &PyArray_Type, &polygon))
	return NULL;

    // verify dimensions first
    if (1 != PyArray_NDIM(point)) 
	return NULL;
    if (6 != point->dimensions[0])
	return NULL;
    if (1 != PyArray_NDIM(polygon)) 
	return 0;

    pgi.setOffsets(polygon);
 
    int ret = checkRect(PGonInfo &pgi,
			*(double *)PyArray_GETPTR1(point, 0), // x
			*(double *)PyArray_GETPTR1(point, 1), // y
			*(double *)PyArray_GETPTR1(point, 2), // xHigh
			*(double *)PyArray_GETPTR1(point, 3), // yHigh
			*(double *)PyArray_GETPTR1(point, 4), // xRes
			*(double *)PyArray_GETPTR1(point, 5)); // yRes

    return PyString_FromFormat("%c", ret);
}

#endif
