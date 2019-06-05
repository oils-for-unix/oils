#!/usr/bin/env python2
"""
oheap2.py

OVM2 stores objects in a data structure called OHeap2.  It has the following
concepts.

- Handles: 4-byte / 32-bit integers that point to Cells.
- Cells: 16-byte structs with a type tag, in a contiguous array.  This array is
  scanned by the GC.
- Slabs: Variable-length arrays of memory that are owned by a Cell.  Each slab
  may be malloc'd individually.
  - In the case of a string, it's opaque to the GC.
  - In the case of a tuple or struct, it must be scanned by the GC.

This is called the "4-16-N design".

Every cell has a type tag, which is simply an integer.  Negative integers
indicate native types implemented in C.  Positive integers are for user-defined
types.

Cells also have an is_slab bit and a length for small.  TODO: is_slab should be
is_small?

Operations on OHeap
-------------------

1. Allocate a new cell, possibly resizing

2. Garbage Collect
  - Walk all the cells.  Free unused cells along with their slabs.

3. Save to file
  Slabs: Native Pointers to Offsets

3a. Copy an object tree to a fresh oheap?  e.g. for IPC.  I guess this is like "Save".
   - Walk all the cells and slabs

4. Load from file into fresh OHeap
  - Patch Slab Offsets to Native Pointers

4a. Load from file and merge into existing OHeap?
    - Inside a namespace?
   - Import?
   - Patch all cell refs!

5. Make permanent?  Move to another "generation"?  OPy classes and bytecode
perhaps fit in this category.

TODO
----

- Bits on handle: whether it's const or not?
  - negative handles could be const?

- Singleton values for None/True/False
- interning of strings
- hash tables, and hashes of strings

Introspection
-------------

These operations should work:

  type()
  getattr() -- hm in OVM I don't want to look at base classes
  dir() -- list all attributes.  ditto -- don't look at base classes?
    hm except this returns different stuff for modules, classes, and objects
    it looks at superclasses
  isinstance(obj, typ) - check if the type tag of obj points at typ or a superclass
"""
from __future__ import print_function

import struct
import sys
import types

from core.util import log


TAG_NONE = -1
TAG_BOOL = -2
TAG_INT = -3
TAG_FLOAT = -4
TAG_STR = -5
TAG_TUPLE = -6
TAG_CODE = -7

MIN_SMALL_INT = -(1 << 63)
MAX_SMALL_INT = (1 << 63) - 1

MAX_LEN_SMALL_STR = 11  # 12 bytes - 1 for NUL

MAX_LEN_SMALL_TUPLE = 3  # 4 Handles in 12 bytes?
                         # We can steal a bit from the tag for the small/big
                         # bit.

def u8(i):  # 1 byte unsigned
  return struct.pack('B', i)

def i16(i):  # 2 bytes
  return struct.pack('h', i)

def i32(i):  # 4 bytes
  return struct.pack('i', i) 

def i64(i):  # 8 bytes (long long)
  return struct.pack('q', i)

def f64(i):  # 8 byte double
  return struct.pack('d', i)


def Align4(i):
  """Round up to the nearest multiple of 4.  See unit tests."""
  return ((i-1) | 3) + 1


def Align16(i):
  """Round up to the nearest multiple of 16.  See unit tests."""
  return ((i-1) | 15) + 1


class Encoder(object):
  """
  Write objects into an OHeap2 structure that can be lazily loaded.

  First pass:
    Append to cells and append to slabs
  Second pass:
    Write slabs as bytes, and then patch offsets in cells?
    Write all the cells
    Write the root object at the front of the file?  Or do it at the end?
    OHeap writes it at the beginnig after
  """

  def __init__(self):
    self.chunk = bytearray()
    # An array of cells
    self.cells = []
    # Write all these first?  So that the cells can point to them.
    self.slabs = []

  def Any(self, obj):
    """
    Encode an object and return its id.
    """
    id_ = len(self.cells)

    # TODO: Enforce that None is a singleton.  But what about joining OHeaps?
    if isinstance(obj, types.NoneType):
      self.cells.append((TAG_NONE, False, None))

    # TODO: Enforce that True/False is a singleton.  But what about joining
    # OHeaps?
    elif isinstance(obj, bool):
      self.cells.append((TAG_BOOL, False, obj))

    elif isinstance(obj, int):
      i = obj
      if MIN_SMALL_INT < i < MAX_SMALL_INT:
        self.cells.append((TAG_INT, False, i))
      else:
        raise NotImplementedError

    elif isinstance(obj, float):
      raise NotImplementedError

    # TODO: Identical strings could be "interned" here.
    elif isinstance(obj, str):
      s = obj
      n = len(s)
      if n < MAX_LEN_SMALL_STR:
        self.cells.append((TAG_STR, False, s))
      else:
        # length and they payload
        slab_index = len(self.slabs)
        self.slabs.append((n, s))
        self.cells.append((TAG_STR, True, slab_index))

    elif isinstance(obj, tuple):
      t = obj
      refs = []
      for item in t:
        refs.append(self.Any(item))  # Depth-first.

      # Compute ID after adding all the children.
      id_ = len(self.cells)

      n = len(t)
      if n < MAX_LEN_SMALL_TUPLE:
        # TODO: How do we know how long it is?
        self.cells.append((TAG_TUPLE, False, refs))
      else:
        slab_index = len(self.slabs)
        self.slabs.append((n, refs))
        self.cells.append((TAG_TUPLE, True, slab_index))

    elif isinstance(obj, types.CodeType):
      co = obj
      refs = []

      # Ints first
      refs.append(self.Any(co.co_argcount))
      refs.append(self.Any(co.co_nlocals))
      refs.append(self.Any(co.co_stacksize))
      refs.append(self.Any(co.co_flags))
      refs.append(self.Any(co.co_firstlineno))

      # Strings
      refs.append(self.Any(co.co_name))
      refs.append(self.Any(co.co_filename))
      refs.append(self.Any(co.co_code))  # bytecode

      # Tuples
      refs.append(self.Any(co.co_names))
      refs.append(self.Any(co.co_varnames))
      refs.append(self.Any(co.co_consts))

      slab_index = len(self.slabs)
      self.slabs.append((len(refs), refs))
      self.cells.append((TAG_CODE, True, slab_index))

    else:
      raise AssertionError

    return id_

  def Write(self, f):
    f.write('OHP2')  # magic header
    f.write(i32(0))  # placeholder for cell offset
    f.write(i32(0))  # placeholder for root object.  NOTE: We could always
                     # fseek(SEEK_END, -4)?  But I think we want it to more
                     # self-describing.

    # Write slabs first, so we know their offsets.
    slab_offsets = []
    pos = 0  # Reader should patch relative to 12

    for length, payload in self.slabs:

      if isinstance(payload, str):
        slab_offsets.append(pos)

        f.write(i32(length))  # length in bytes
        pos += 4

        n = len(payload)
        aligned = Align4(n+1)  # at least NUL byte for terminator
        f.write(payload)
        f.write('\0' * (aligned - n))  # padding
        pos += aligned

      elif isinstance(payload, list):  # list of references
        slab_offsets.append(pos)

        # length in references.  Could be unsigned?
        f.write(i32(length))

        # NOTE: There is no GC offset, since all of them are scanned?
        for ref in payload:
          f.write(i32(ref))
        pos += 4
        pos += len(payload) * 4

      else:
        raise AssertionError(payload)

    log('Slab offsets: %s', slab_offsets)

    # Pad out the slabs so that the cells begins at a multiple of 16.
    total_slab_size = Align16(pos)  # including pad, but not including header.
    f.write('\0' * (total_slab_size - pos))  # Write the pad

    # Encode it into 16 bytes
    for tag, is_slab, val in self.cells:
      #log('%s %s %s', tag, is_slab, val)

      # 4 byte tag.  This may be patched into a type Handle?
      # Reserve LSB for is_slab?  Or highest bit?
      # The tag could be (i >> 1) then?
      f.write(i16(tag))

      if tag == TAG_NONE:
        f.write(i16(0))
        f.write(i32(0))
        f.write(i32(0))
        f.write(i32(0))

      elif tag == TAG_BOOL:
        f.write(i16(0))  # pad
        f.write(i32(0))  # pad
        f.write(i32(0))  # pad
        f.write(i32(int(val)))  # 0 or 1

      elif tag == TAG_INT:
        assert not is_slab, val
        f.write(i16(0))  # Padding
        f.write(i32(0))  # Padding
        f.write(i64(val))

      elif tag == TAG_FLOAT:
        assert not is_slab, val
        f.write(i16(0))  # Padding
        f.write(i32(0))  # Padding
        f.write(f64(val))

      elif tag == TAG_STR:
        if is_slab:
          # For a string, a big/small bit could technically be in the last
          # byte.  To reuse NUL terminator.  But I want the patching process to
          # be consistent.
          slab_index = val
          offset = slab_offsets[slab_index]
          f.write(u8(1))  # is_slab
          f.write(u8(0))  # length stored in slab
          f.write(i32(0))  # pad
          f.write(i32(0))  # pad
          f.write(i32(offset))
        else:
          n = len(val)
          f.write(u8(0))  # is_slab
          f.write(u8(n))  # length stored here
          f.write(val)
          num_pad = 12 - n  # at least one NUL
          f.write('\0' * num_pad)

      elif tag == TAG_TUPLE:
        if is_slab:
          slab_index = val
          offset = slab_offsets[slab_index]
          f.write(u8(1))  # is_slab
          f.write(u8(0))  # length stored in slab
          f.write(i32(0))  # pad
          f.write(i32(0))  # pad
          f.write(i32(offset))
        else:
          n = len(val)
          f.write(u8(0))  # is_slab
          f.write(u8(n))
          # TODO: how is length represented?
          for ref in val:
            f.write(i32(ref))
          num_pad = 3 - len(val)
          for i in xrange(num_pad):
            f.write(i32(0))

      elif tag == TAG_CODE:
        assert is_slab, val
        slab_index = val
        #log('slab_index %d', slab_index)
        offset = slab_offsets[slab_index]
        f.write(u8(1)) # is_slab
        f.write(u8(0)) # length stored in slab
        f.write(i32(0))  # pad
        f.write(i32(0))  # pad
        f.write(i32(offset))

      else:
        raise AssertionError(tag)

    log('')
    log('slabs')
    for slab in self.slabs:
      log('\t%r', slab)

    log('cells')
    for c in self.cells:
      #log('\t%r', c)
      pass

    log('%d slabs in %d bytes', len(self.slabs), total_slab_size)
    log('%d cells in %d bytes', len(self.cells), f.tell() - 12 - total_slab_size)

    # Fill in the cell position
    f.seek(4)
    f.write(i32(total_slab_size))
    f.write(i32(len(self.cells)))


def Write(co, f):
  print(co)
  enc = Encoder()
  enc.Any(co)
  enc.Write(f)


def main(argv):
  chunk = bytearray()
  chunk.extend('hello')
  chunk.append('\0')

  print('Hello from oheap2.py')
  print(repr(chunk))


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
