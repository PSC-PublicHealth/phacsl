import lmdb, msgpack
import time, datetime, shutil, os
import numpy as np
from retrying import retry
try:
    import cPickle as pickle
except:
    import pickle
import collections

#import blosc
#from pyhashxx import hashxx

def retryable(exception):
    return isinstance(exception, lmdb.BadRslotError)

_RaiseKeyError = object()

def timestamp():
    return '{:%Y.%m.%d_}'.format(datetime.datetime.now()) + str(time.time())

_allowed_serialization_types = ['msgpack', 'pickle']

def _validate_and_set_serialization_args(self, convert_int, key_serialization,
        val_serialization, integer_keys):
    if not integer_keys and  key_serialization not in _allowed_serialization_types:
        raise Exception('If integer_keys is False, then valid key_serialization must be given!')
    if convert_int and key_serialization is not None:
        raise Exception('Does not make sense to use convert_int and key_serialization')
    self.integer_keys = integer_keys
    self.convert_int = convert_int
    if self.convert_int and key_serialization is not None:
        raise Exception('key_serialization must be None if convert_int is True!')
    elif key_serialization is None or key_serialization in _allowed_serialization_types:
        self.key_serialization = key_serialization
    else:
        raise Exception('Invalid key_serialization requested!')
    if val_serialization in _allowed_serialization_types:
        self.val_serialization = val_serialization
    else:
        raise Exception('Invalid val_serialization requested!')
    if key_serialization is not None or convert_int:
        self.convert_key = True

class InterDictFactory(object):
    def __init__(self, dbdir, overwrite_existing=True, convert_int=True,
            append_timestamp=True, key_serialization=None,
            val_serialization='msgpack', integer_keys=True):

        self.dbdir = dbdir
        self.overwrite_existing = overwrite_existing
        self.append_timestamp = append_timestamp

        _validate_and_set_serialization_args(self, convert_int,
                key_serialization, val_serialization, integer_keys) 

    def __call__(self, *args, **kwargs):
        if self.append_timestamp:
            dbdir = '%s.%s' % (self.dbdir, timestamp())
        else:
            dbdir = self.dbdir
        d = InterDict(dbdir, self.overwrite_existing, self.convert_int,
                self.key_serialization, self.val_serialization, self.integer_keys,
                *args, **kwargs)
        return d

class InterDict(dict):
    """
    Creates an lmdb backed dict.
    
    keys can either be integer or string/bytes based.  
    If integer based they must be passed as a (numpy) int64 or the convert_int flag must be set.

    vals are string/bytes based.
    
    To be more useful in python, InterDicts can take python objects and serialize them with either
    pickle or msgpack for either or both of keys and vals.

    """
    def get_packing_functions(self):
        if self.convert_int:
            kpf = lambda x: self.int(x)
            kupf = lambda x: x
        elif self.key_serialization == 'msgpack':
            kpf = lambda x: msgpack.packb(x)
            kupf = lambda x: msgpack.unpackb(x)
        elif self.key_serialization == 'pickle':
            kpf = lambda x: pickle.dumps(x, protocol=2)
            kupf = lambda x: pickle.loads(bytes(x))
        elif self.key_serialization is None:
            kpf = lambda x: x
            kupf = lambda x: x
        else:
            raise RuntimeError("unknown key serialization")
        if self.val_serialization == 'msgpack':
            vpf = lambda x: msgpack.packb(x)
            vupf = lambda x: msgpack.unpackb(x)
        elif self.val_serialization == 'pickle':
            vpf = lambda x: pickle.dumps(x, protocol=2)
            vupf = lambda x: pickle.loads(bytes(x))
        elif self.val_serialization is None:
            vpf = lambda x: x
            vupf = lambda x: x
        else:
            raise RuntimeError("unknown val serialization")
        return kpf,kupf,vpf,vupf 

    def __init__(self, dbdir, overwrite_existing=False, convert_int=False,
            key_serialization=None, val_serialization='msgpack',
            integer_keys=True, *args, **kwargs):

        self.overwrite_existing = overwrite_existing
        if os.path.exists(dbdir):
            if overwrite_existing:
                shutil.rmtree(dbdir)
        self.dbdir = dbdir if isinstance(dbdir, bytes) else dbdir.encode()

        _validate_and_set_serialization_args(self, convert_int,
                key_serialization, val_serialization, integer_keys) 

        self.pack_key,self.unpack_key,self.pack_val,self.unpack_val = self.get_packing_functions()

        self.env = lmdb.open(dbdir, max_dbs=1,
                map_size=int(1e10),
                max_readers=253,
                map_async=True,
                writemap=True,
                max_spare_txns=126
                )
        self.db = self.env.open_db(b'db', integerkey=self.integer_keys)

        if args is not None:
            self.mset(args)
        elif kwargs is not None:
            self.mset(kwargs.items())

    def int(self, i):
        return np.int64(i)

    def __setitem__(self, key, val):
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                txn.put(self.pack_key(key), self.pack_val(val), db=self.db)
        except Exception as e:
            raise

    @retry(wait_fixed=100, stop_max_attempt_number=10, retry_on_exception=retryable)
    def __getitem__(self, key):
        try:
            with self.env.begin(write=False, buffers=True) as txn:
                return self.unpack_val(txn.get(self.pack_key(key), db=self.db))
        except Exception as e:
            raise

    def __delitem__(self, key):
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                txn.delete(self.pack_key(key), db=self.db)
        except Exception as e:
            raise

    @retry(wait_fixed=100, stop_max_attempt_number=10, retry_on_exception=retryable)
    def __contains__(self, key):
        with self.env.begin(write=False, buffers=True) as txn:
            return txn.get(self.pack_key(key), db=self.db) is not None

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
            if self.integer_keys:
                return [np.frombuffer(key, dtype='int64')[0] for key,_ in txn.cursor(db=self.db)]
            else:
                return [self.unpack_key(key) for key,_ in txn.cursor(db=self.db)]
            
    def keyRange(self, kMin, kMax):
        kMin = self.pack_key(kMin)
        kMax = self.pack_key(kMax)

        ret = []
        with self.env.begin(write=False, buffers=True) as txn:
            if self.integer_keys:
                cursor =  txn.cursor(db=self.db)
                cursor.set_range(kMin)
                for key,_ in cursor:
                    key = np.frombuffer(key, dtype='int64')[0]
                    if key > kMax:
                        return ret
                    ret.append(key)
                return ret
            else:
                cursor =  txn.cursor(db=self.db)
                cursor.set_range(kMin)
                for key,_ in cursor:
                    key = self.unpack_key(key)
                    if key > kMax:
                        return ret
                    ret.append(key)
                return ret

        

    def values(self):
        with self.env.begin(write=False, buffers=True) as txn:
            return [self.unpack_val(val) for _,val in txn.cursor(db=self.db)]

    def iteritems(self):
        with self.env.begin(write=False, buffers=True) as txn:
            if self.integer_keys:
                for key, val in txn.cursor(db=self.db):
                    yield np.frombuffer(key, dtype='int64')[0], self.unpack_val(val)
            else:
                for key, val in txn.cursor(db=self.db):
                    yield self.unpack_key(key), self.unpack_val(val)
    
    def items(self):
        return [tpl for tpl in self.iteritems()]

    def mset(self, items):
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                for key, val in items:
                    txn.put(self.pack_key(key), self.pack_val(val), db=self.db)
        except Exception as e:
            raise

    def mset_single_value(self, keys, val):
        """ Set multiple keys to the same value, within a single transaction """
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                for key in keys:
                    txn.put(self.pack_key(key), self.pack_val(val), db=self.db)
        except Exception as e:
            raise

    def mget(self, keys):
        try:
            with self.env.begin(write=False, buffers=True) as txn:
                for key in keys:
                    yield key, self.unpack_val(txn.get(self.pack_key(key), db=self.db))
        except Exception as e:
            raise

    def mdel(self, keys):
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                for key in keys:
                    txn.delete(self.pack_key(key), db=self.db)
        except Exception as e:
            raise

    def get_and_set(self, key, setter):
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                val = self.get(key)
                self[key] = setter(val)
                return val
        except Exception as e:
            raise

    def __repr__(self):
        return '{0}({1})'.format(type(self).__name__, str(self.items()))

    def flush(self):
        self.env.sync()

    def close(self):
        self.env.close()


class IntValueInterDict(InterDict):

    def debit(self, key, amount, min_remaining=np.iinfo('int').min):
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                val = self.unpack_val(txn.get(self.pack_key(key), db=self.db))
                if val < min_remaining:
                    remaining_debit_amount = amount
                else:
                    val = val - amount
                    if val < min_remaining:
                        remaining_debit_amount = min_remaining - val 
                        val = min_remaining
                    else:
                        remaining_debit_amount = 0
                txn.put(self.pack_key(key), self.pack_val(val), db=self.db)
                return val, remaining_debit_amount
        except Exception as e:
            raise

    def credit(self, key, amount, max_remaining=np.iinfo('int').max):
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                val = self.unpack_val(txn.get(self.pack_key(key), db=self.db))
                if val > max_remaining:
                    remaining_credit_amount = amount
                else:
                    val = val + amount
                    if val > max_remaining:
                        remaining_credit_amount = val - max_remaining 
                        val = max_remaining
                    else:
                        remaining_credit_amount = 0
                txn.put(self.pack_key(key), self.pack_val(val), db=self.db)
                return val, remaining_credit_amount
        except Exception as e:
            raise

    def mdebit(self, keys, amount, min_remaining=np.iinfo('int').min):
        assert(isinstance(keys, collections.Iterable))
        if isinstance(amount, collections.Iterable):
            assert(len(keys)==len(amount))
            amount = np.asarray(amount, dtype=int)
        else:
            amount = np.zeros(len(keys), dtype=int) + amount
        if isinstance(min_remaining, collections.Iterable):
            assert(len(keys)==len(min_remaining))
            min_remaining = np.asarray(min_remaining, dtype=int)
        else:
            min_remaining = np.zeros(len(keys), dtype=int) + min_remaining
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                cur_vals = []
                for key in keys:
                    cur_vals.append(self.unpack_val(
                        txn.get(self.pack_key(key), db=self.db)))
                vals = np.asarray(cur_vals, dtype=int)
                remaining_debit_amount = np.zeros(len(keys), dtype=int)
                for key,i in zip(keys, range(len(vals))):
                    if vals[i] < min_remaining[i]:
                        remaining_debit_amount[i] = amount[i]
                    else:
                        vals[i] = vals[i] - amount[i]
                        if vals[i] < min_remaining[i]:
                            remaining_debit_amount[i] = min_remaining[i] - vals[i]
                            vals[i] = min_remaining[i]
                        else:
                            remaining_debit_amount[i] = 0
                    val = int(vals[i])
                    txn.put(self.pack_key(key), self.pack_val(val), db=self.db)
                return vals, remaining_debit_amount
        except Exception as e:
            raise

    def mcredit(self, keys, amount, max_remaining=np.iinfo('int').max):
        assert(isinstance(keys, collections.Iterable))
        if isinstance(amount, collections.Iterable):
            assert(len(keys)==len(amount))
            amount = np.asarray(amount, dtype=int)
        else:
            amount = np.zeros(len(keys), dtype=int) + amount
        if isinstance(max_remaining, collections.Iterable):
            assert(len(keys)==len(max_remaining))
            max_remaining = np.asarray(max_remaining, dtype=int)
        else:
            max_remaining = np.zeros(len(keys), dtype=int) + max_remaining
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                cur_vals = []
                for key in keys:
                    cur_vals.append(self.unpack_val(
                        txn.get(self.pack_key(key), db=self.db)))
                vals = np.asarray(cur_vals, dtype=int)
                remaining_credit_amount = np.zeros(len(keys), dtype=int)
                for key,i in zip(keys, range(len(vals))):
                    if vals[i] > max_remaining[i]:
                        remaining_credit_amount[i] = amount[i]
                    else:
                        vals[i] = vals[i] + amount[i]
                        if vals[i] > max_remaining[i]:
                            remaining_credit_amount[i] = vals[i] - max_remaining[i]
                            vals[i] = max_remaining[i]
                        else:
                            remaining_credit_amount[i] = 0
                    val = int(vals[i])
                    txn.put(self.pack_key(key), self.pack_val(val), db=self.db)
                return vals, remaining_credit_amount
        except Exception as e:
            raise

    def mcredit_from_pool(self, keys, pool, max_remaining):
        assert(isinstance(keys, collections.Iterable))
        assert(not isinstance(pool, collections.Iterable))
        if isinstance(max_remaining, collections.Iterable):
            assert(len(keys)==len(max_remaining))
            max_remaining = np.asarray(max_remaining, dtype=int)
        else:
            max_remaining = np.zeros(len(keys), dtype=int) + max_remaining
        try:
            with self.env.begin(write=True, buffers=True) as txn:
                cur_vals = []
                for key in keys:
                    cur_vals.append(self.unpack_val(
                        txn.get(self.pack_key(key), db=self.db)))
                vals = np.asarray(cur_vals, dtype=int)
                for key,i in zip(keys, range(len(vals))):
                    if vals[i] < max_remaining[i]:
                        if pool >= max_remaining[i] - vals[i]:
                            pool -= max_remaining[i] - vals[i]
                            vals[i] = max_remaining[i]
                        else:
                            vals[i] += pool
                            pool = 0
                    val = int(vals[i])
                    txn.put(self.pack_key(key), self.pack_val(val), db=self.db)
                    if pool < 0:
                        raise Exception()
                    elif pool == 0:
                        break
                return vals, pool
        except Exception as e:
            raise

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
