import lmdb, msgpack
#import blosc
#from pyhashxx import hashxx

_RaiseKeyError = object()

class InterDict(dict):
    
    @staticmethod
    def unpack(v):
#        return msgpack.unpackb(blosc.decompress(v))
        return msgpack.unpackb(v)

    @staticmethod
    def pack(v):
#        return blosc.compress(msgpack.packb(v)) 
        return msgpack.packb(v)

    def __init__(self, dbdir, overwrite_existing=False):
        self.dbdir = dbdir if isinstance(dbdir, bytes) else dbdir.encode()
        self.env = lmdb.open(dbdir, max_dbs=1, map_size=int(1e9))
        self.db = self.env.open_db(b'db', integerkey=True)

    def __setitem__(self, key, val):
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                txn.put(key, InterDict.pack(val), db=self.db)
        except Exception as e:
            raise

    def __getitem__(self, key):
        try:
            with self.env.begin(write=False, buffers=True) as txn:
                return InterDict.unpack(txn.get(key, db=self.db))
        except Exception as e:
            raise

    def __delitem__(self, key):
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                txn.delete(key, db=self.db)
        except Exception as e:
            raise

    def __contains__(self, key):
        with self.env.begin(write=False, buffers=True) as txn:
            return txn.get(key, db=self.db) is not None

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
            v = self.__getitem(key)
            self.__delitem__(key)
        else:
            try:
                v = self.get(key, default)
                self.__delitem__(key)
            except:
                pass
            finally:
                return v

    def update(self, mapping=(), **kwargs):
        if getattr(mapping, 'keys'):
            for k in mapping.keys():
                self.__setitem__(k, mapping[k])
        else:
            for k, v in mapping:
                self.__setitem__(k, v)
        self.update(mapping=kwargs)

    def copy(self, dbdir=None, overwrite_existing=False):
        if dbdir is None:
            dbdir = self.dbdir + b'.Copy'
        else:
            dbdir = dbdir if isinstance(dbdir, bytes) else dbdir.encode()
        copy = type(self)(dbdir, overwrite_existing)
        copy.update(self)
        return copy

    def mset(self, items):
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                for key, val in items:
                    txn.put(key, InterDict.pack(val), db=self.db)
        except Exception as e:
            raise

    def mget(self, keys):
        try:
            with self.env.begin(write=False, buffers=True) as txn:
                for key in keys:
                    yield key, InterDict.unpack(txn.get(key, db=self.db))
        except Exception as e:
            raise

    def mdel(self, keys):
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                for key in keys:
                    txn.delete(key, db=self.db)
        except Exception as e:
            raise


