import lmdb, msgpack
import time, datetime, shutil, os
import numpy as np

#import blosc
#from pyhashxx import hashxx

_RaiseKeyError = object()

def timestamp():
    return '{:%Y.%m.%d_}'.format(datetime.datetime.now()) + str(time.time())

class InterDictFactory(object):
    def __init__(self, dbdir, overwrite_existing=True, convert_int=True, append_timestamp=True):
        self.dbdir = dbdir
        self.overwrite_existing = overwrite_existing
        self.append_timestamp = append_timestamp
        self.convert_int = True
    
    def __call__(self, *args, **kwargs):
        if self.append_timestamp:
            dbdir = '%s.%s' % (self.dbdir, timestamp())
        else:
            dbdir = self.dbdir
        d = InterDict(dbdir, self.overwrite_existing, self.convert_int, *args, **kwargs)
        return d

class InterDict(dict):
    
    @staticmethod
    def unpack(v):
#        return msgpack.unpackb(blosc.decompress(v))
        return msgpack.unpackb(v)

    @staticmethod
    def pack(v):
#        return blosc.compress(msgpack.packb(v)) 
        return msgpack.packb(v)

    def __init__(self, dbdir, overwrite_existing=False, convert_int=False, *args, **kwargs):
        self.overwrite_existing = overwrite_existing
        if os.path.exists(dbdir):
            if overwrite_existing:
                shutil.rmtree(dbdir)
        self.dbdir = dbdir if isinstance(dbdir, bytes) else dbdir.encode()
        self.convert_int = convert_int
        self.env = lmdb.open(dbdir, max_dbs=1, map_size=int(1e9))
        self.db = self.env.open_db(b'db', integerkey=True)
        if args is not None:
            self.mset(args)
        elif kwargs is not None:
            self.mset(kwargs.items())

    def int(self, i):
        return np.int64(i)

    def __setitem__(self, key, val):
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                if self.convert_int:
                    txn.put(self.int(key), InterDict.pack(val), db=self.db)
                else:
                    txn.put(key, InterDict.pack(val), db=self.db)
        except Exception as e:
            raise

    def __getitem__(self, key):
        try:
            with self.env.begin(write=False, buffers=True) as txn:
                if self.convert_int:
                    return InterDict.unpack(txn.get(self.int(key), db=self.db))
                else:
                    return InterDict.unpack(txn.get(key, db=self.db))
        except Exception as e:
            raise

    def __delitem__(self, key):
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                if self.convert_int:
                    txn.delete(self.int(key), db=self.db)
                else:
                    txn.delete(key, db=self.db)
        except Exception as e:
            raise

    def __contains__(self, key):
        with self.env.begin(write=False, buffers=True) as txn:
            if self.convert_int:
                return txn.get(self.int(key), db=self.db) is not None
            else:
                return txn.get(key, db=self.db) is not None

    def __len__(self):
        with self.env.begin(write=False, buffers=True) as txn:
            return txn.stat(db=self.db)['entries']

    def get(self, key, default=None):
        try:
            return self.__getitem__(key)
        except Exception as e:
            return default

    def setdefault(self, key, default=None):
        self.__setitem__(key, default)
        if default is not None:
            return default

    def pop(self, key, default=_RaiseKeyError):
        if default is _RaiseKeyError:
            v = self.__getitem__(key)
            self.__delitem__(key)
            return v
        else:
            try:
                v = self.get(key, default)
                self.__delitem__(key)
            except:
                pass
            finally:
                return v

    def update(self, mapping=(), **kwargs):
        if hasattr(mapping, 'keys'):
            self.mset(mapping.items())
        else:
            self.mset(mapping)
        if len(kwargs) > 0:
            self.update(mapping=kwargs)

    def copy(self, dbdir=None, overwrite_existing=True):
        if dbdir is None:
            dbdir = self.dbdir + b'.copied.' + (timestamp()).encode()
        else:
            dbdir = dbdir if isinstance(dbdir, bytes) else dbdir.encode()
        copy = type(self)(dbdir, overwrite_existing)
        copy.update(self)
        return copy

    def keys(self):
        with self.env.begin(write=False, buffers=True) as txn:
            return [np.frombuffer(key, dtype='int64')[0] for key,_ in txn.cursor(db=self.db)]

    def values(self):
        with self.env.begin(write=False, buffers=True) as txn:
            return [InterDict.unpack(val) for _,val in txn.cursor(db=self.db)]

    def iteritems(self):
        with self.env.begin(write=False, buffers=True) as txn:
            for key, val in txn.cursor(db=self.db):
                yield np.frombuffer(key, dtype='int64')[0], InterDict.unpack(val)
    
    def items(self):
        return [tpl for tpl in self.iteritems()]

    def mset(self, items):
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                if self.convert_int:
                    for key, val in items:
                        txn.put(self.int(key), InterDict.pack(val), db=self.db)
                else:
                    for key, val in items:
                        txn.put(key, InterDict.pack(val), db=self.db)
        except Exception as e:
            raise

    def mget(self, keys):
        try:
            with self.env.begin(write=False, buffers=True) as txn:
                if self.convert_int:
                    for key in keys:
                        yield key, InterDict.unpack(txn.get(self.int(key), db=self.db))
                else:
                    for key in keys:
                        yield key, InterDict.unpack(txn.get(key, db=self.db))

        except Exception as e:
            raise

    def mdel(self, keys):
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                if self.convert_int:
                    for key in keys:
                        txn.delete(self.int(key), db=self.db)
                else:
                    for key in keys:
                        txn.delete(key, db=self.db)
        except Exception as e:
            raise

    def __repr__(self):
        return '{0}({1})'.format(type(self).__name__, str(self.items()))


import unittest, tempfile

class TestInterDictFactory(unittest.TestCase):

    def runTest(self):
        self.test_basic_usage()
    
    def test_basic_usage(self):
        dbdir = tempfile.mkdtemp()
        f = InterDictFactory(dbdir)
        self.assertEqual(f.append_timestamp, True)
        
        for i in range(2):
            d = f()
            self.assertEqual(d.overwrite_existing, True)
            self.assertEqual(d.convert_int, True)
            testlen = 10
            items = list(zip(range(testlen),range(testlen)))
            d.update(items)
            self.assertEqual(len(d),testlen)
            for k,v in items:
                self.assertIn(k, d)
                self.assertEqual(v,d[k])

if __name__ == '__main__':
        unittest.main()
