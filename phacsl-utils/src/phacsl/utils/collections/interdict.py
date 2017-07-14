import lmdb, msgpack
#import blosc
#from pyhashxx import hashxx

class InterDict(object):
    
    @staticmethod
    def unpack(v):
#        return msgpack.unpackb(blosc.decompress(v))
        return msgpack.unpackb(v)

    @staticmethod
    def pack(v):
#        return blosc.compress(msgpack.packb(v)) 
        return msgpack.packb(v)

    def __init__(self, dbdir):
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


