#cython: boundscheck=False, wraparound=False

import collections

import cython
from cython.operator cimport dereference, preincrement, postincrement

import numpy as np
cimport numpy as np

from openmp cimport (
        omp_lock_t, omp_init_lock, omp_destroy_lock,
        omp_set_lock, omp_unset_lock, omp_test_lock)

from libcpp.vector cimport vector as cpp_vector

# NOTE: This extension class ALWAYS uses unsigned 64-bit integers
# NOTE: This isn't automatically thread-safe, however it is possible
# NOTE: lock and unlock externally

cdef class Bitset:

    cdef:
        np.uint64_t [:] array_view
        omp_lock_t _lock
        int num_bits, num_ints

    def __cinit__(self, *args, **kwargs):
        if len(args) != 1:
            raise ValueError(
                    'Bitset constructor only accepts a single positional argument')
        if not isinstance(args[0], int):
            raise ValueError(
                    'Bitset constructor only accepts an int as its single positional argument')
        self.num_bits = args[0]
        self.num_ints = ((self.num_bits-1) // 64) + 1
        self.array_view = np.zeros(self.num_ints, dtype='uint64')

    cdef inline void lock(self) nogil:
        omp_set_lock(&self._lock)

    cdef inline void unlock(self) nogil:
        omp_unset_lock(&self._lock)

    cdef int size(self) nogil:
        return self.num_bits

    def __len__(self):
        return self.size()

    cdef bint test(self, int bit) nogil:
        if bit >= self.num_bits:
            with gil:
                raise IndexError()
        else:
            self.lock()
        cdef int int_idx = bit // 64
        cdef int bit_idx = bit % 64
        cdef np.uint64_t one = 1
        cdef bint isset
        if self.array_view[int_idx] & (one<<bit_idx):
            isset = 1
        else:
            isset = 0
        self.unlock()
        return isset

    def __getitem__(self, key):
        if isinstance(key, slice):
            return [self.test(i) for i in range(*key.indices(self.num_bits))]
        elif isinstance(key, collections.Iterable):
            return [self.test(i) for i in key]
        else:
            return self.test(key)

    cdef void set(self, int bit) nogil:
        if bit >= self.num_bits:
            with gil:
                raise IndexError()
        else:
            self.lock()
        cdef int int_idx = bit // 64
        cdef int bit_idx = bit % 64
        cdef np.uint64_t one = 1
        self.array_view[int_idx] = self.array_view[int_idx] | (one<<bit_idx)
        self.unlock()

    cdef void unset(self, int bit) nogil:
        if bit >= self.num_bits:
            with gil:
                raise IndexError()
        else:
            self.lock()
        cdef int int_idx = bit // 64
        cdef int bit_idx = bit % 64
        cdef np.uint64_t one = 1
        self.array_view[int_idx] = self.array_view[int_idx] & ~(one<<bit_idx)
        self.unlock()

    def __setitem__(self, key, value):

        def apply_single_value_to_slice(key, value):
            if value:
                for i in range(*key.indices(self.num_bits)): self.set(i)
            else:
                for i in range(*key.indices(self.num_bits)): self.unset(i)
        def apply_single_value_to_single_key(key, value):
            if value: self.set(key)
            else: self.unset(key)
        def apply_bitstring_to_slice(key, value):
            for i,v in zip(range(*key.indices(self.num_bits)), value):
                if int(v, 2): self.set(i)
                else: self.unset(i)
        def apply_iterable_to_slice(key, value):
            for i,v in zip(range(*key.indices(self.num_bits)), value):
                if v: self.set(i)
                else: self.unset(i)

        if isinstance(key, slice):
            if isinstance(value, bytes):
                value = value.decode()
            if isinstance(value, str):
                if value[0:2] == '0b':
                    value = value[2:]
            if isinstance(value, collections.Iterable):
                if len(range(*key.indices(self.num_bits))) != len(value):
                    raise IndexError(
                            'Length of slice (%d) does not match length of values (%d)' % (
                                len(range(*key.indices(self.num_bits))), len(value)))
                if isinstance(value, str):
                    apply_bitstring_to_slice(key, value)
                else:
                    apply_iterable_to_slice(key, value)
            else:
                apply_single_value_to_slice(key, value)
        else:
            apply_single_value_to_single_key(key, value)

    cpdef Bitset bitwise(Bitset self, Bitset other, str oper):
        if self.num_bits != other.num_bits:
            raise IndexError('Bitsets must have the same size!')
        result = Bitset(self.num_bits)
        self.lock()
        other.lock()
        if oper == 'and':
            result.array_view = np.asarray(self.array_view) & np.asarray(other.array_view)
        elif oper == 'or':
            result.array_view = np.asarray(self.array_view) | np.asarray(other.array_view)
        elif oper == 'xor':
            result.array_view = np.asarray(self.array_view) ^ np.asarray(other.array_view)
        self.unlock()
        other.unlock()
        return result

    def __and__(self, other):
        return self.bitwise(other, 'and')

    def __or__(self, other):
        return self.bitwise(other, 'or')

    def __xor__(self, other):
        return self.bitwise(other, 'xor')

    cpdef Bitset insert(self, index, value):
        if isinstance(value, bytes):
            value = value.decode()
        if isinstance(value, str):
            if value[0:2] == '0b':
                value = value[2:]
        result = Bitset(self.num_bits + len(value))
        result.array_view[:self.num_ints] = self.array_view[:self.num_ints]
        #result[:index] = self[:index]
        result[index+len(value):] = self[index:]
        result[index:index+len(value)] = value
        return result

    cpdef np.uint64_t [:] memoryview(self):
        return self.array_view

























