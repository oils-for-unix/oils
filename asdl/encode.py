#!/usr/bin/python
"""
encode.py
"""

import sys

from asdl import asdl_parse
from asdl import py_meta
asdl = asdl_parse  # ALIAS

_DEFAULT_ALIGNMENT = 4


class BinOutput:
  """Write aligned blocks here.  Keeps track of block indexes for refs."""

  def __init__(self, f, alignment=_DEFAULT_ALIGNMENT):
    self.f = f
    # index of last block, to return as a ref.
    self.last_block = 0
    self.alignment = alignment

  def WriteRootRef(self, chunk):
    self.f.seek(5)  # seek past 'OHP\x01\x04'

    assert len(chunk) == 3
    self.f.write(chunk)

  def Write(self, chunk):
    """
    Return a block pointer/index.
    """
    # Input should be padded
    a = self.alignment
    assert len(chunk) % self.alignment == 0
    self.f.write(chunk)

    ref = self.last_block
    num_blocks = len(chunk) // self.alignment  # int division
    #print('WROTE %d blocks' % num_blocks)
    self.last_block += num_blocks

    # Return a reference to the beginning
    return ref


class Params:
  """Encoding parameters.

  Hm most of these settings should be per-field, expressed in the schema.  The
  only global one is the ref/pointer alignment.  4 and 8 are the most likely
  choices, and 4 is probably fine, because you have 64 MB of addressable memory
  with 24 bit pointers.
  """

  def __init__(self, alignment=_DEFAULT_ALIGNMENT):
    self.alignment = alignment
    self.pointer_type = 'uint32_t'

    self.tag_width = 1  # for ArithVar vs ArithWord.
    self.ref_width = 3  # 24 bits
    self.int_width = 3  # 24 bits
    # used for fd, line/col
    # also I guess steuff like SimpleCommand
    self.index_width = 2  # 16 bits, e.g. max 64K entries in an array

    self.max_int = 1 << (self.ref_width * 8)
    self.max_index = 1 << (self.index_width * 8)
    self.max_tag = 1 << (self.tag_width * 8)

  def Tag(self, i, chunk):
    if i > self.max_tag:
      raise AssertionError('Invalid id %r' % i)
    chunk.append(i & 0xFF)

  def Int(self, n, chunk):
    if n > self.max_int:
      raise Error('%d is too big to fit in %d bytes' % (n, self.int_width))

    for i in range(self.int_width):
      chunk.append(n & 0xFF)
      n >>= 8

  def Ref(self, n, chunk):
    self.Int(n, chunk)

  def _Pad(self, chunk):
    n = len(chunk)
    a = self.alignment
    if n % a != 0:
      chunk.extend(b'\x00' * (a - (n % a)))
    return chunk

  # Right now all strings are references.  Later they could be inline.
  def Str(self, s, chunk):
    # NOTE: For variable, proc, and function names, it could make sense to
    # pre-compute and store a hash value.  They will be looked up in the stack
    # and so forth.
    # - You could also return a obj number or object ID.
    chunk.extend(s.encode('utf-8'))
    chunk.append(0)  # NUL terminator

  def PaddedStr(self, s):
    # NOTE:
    # - The encoder could also have an intern table to save space.
    # - Str and PaddedStr will both return char* ?  Should we allow them to
    # VARY with the same schema, is a value/ref type PART of the schema?  It's
    # basically small size optimization and "flexible array" optimization.  I
    # think you want that possibility.
    chunk = bytearray()
    self.Str(s, chunk)
    return self._Pad(chunk)

  def Bytes(self, buf, chunk):
    n = len(buf)
    if n >= self.max_index:
      raise RuntimeError("bytes object is too long (%d)" % n)
    for i in range(self.index_width):
      chunk.append(n & 0xFF)
      n >>= 8
    chunk.extend(buf.encode('utf-8'))

  def PaddedBytes(self, buf):
    chunk = bytearray()
    self.Bytes(buf, chunk)
    return self._Pad(chunk)

  def PaddedBlock(self, chunk):
    return self._Pad(chunk)


def EncodeArray(obj_list, item_desc, enc, out):
  """
  Args:
    obj_list: List of Obj values

  Returns:
    ref
  """
  array_chunk = bytearray()
  enc.Int(len(obj_list), array_chunk)  # Length prefix

  if isinstance(item_desc, asdl.IntType):
    for item in obj_list:
      enc.Int(item, array_chunk)

  elif isinstance(item_desc, asdl.Sum) and asdl.is_simple(item_desc):
    for item in obj_list:
      enc.Int(item.enum_id, array_chunk)

  else:

    # A simple value is either an int, enum, or pointer.  (Later: Iter<Str>
    # might be possible for locality.)
    assert isinstance(item_desc, asdl.Sum) or isinstance(
        item_desc, asdl.Product), item_desc

    # This is like vector<T*>
    # Later:
    # - Product types can be put in line
    # - Sum types can even be put in line, if you have List<T> rather than
    # Array<T>.  Array implies O(1) random access; List doesn't.
    for item in obj_list:
      # Recursive call.
      ref = EncodeObj(item, enc, out)
      enc.Ref(ref, array_chunk)

  this_ref = out.Write(enc.PaddedBlock(array_chunk))
  return this_ref


def EncodeObj(obj, enc, out):
  """
  Args:
    obj: Obj to encode
    enc: encoding params
    out: output file

  Returns:
    ref: Reference to the last block
  """
  # Algorithm: Depth first, post-order traversal.  First obj is the first leaf.
  # last obj is the root.
  #
  # Array is a homogeneous type.

  this_chunk = bytearray()
  assert isinstance(obj, py_meta.CompoundObj), \
    '%s is not a compound obj (%r)' % (obj, obj.__class__)

  if isinstance(obj.DESCRIPTOR, asdl.Constructor):
    enc.Tag(obj.tag, this_chunk)

  for name in obj.FIELDS:  # encode in order
    desc = obj.DESCRIPTOR_LOOKUP[name]
    #print('\n\n------------')
    #print('field DESC', name, desc)

    field_val = getattr(obj, name)
    #print('VALUE', field_val)

    # TODO:
    # - Float would be inline, etc.
    # - Optional value: write all enc.Ref(0)?  This is 'nullptr'.
    # - Repeated value: write them all adjacent to each other?

    # INLINE
    if isinstance(desc, asdl.IntType):
      enc.Int(field_val, this_chunk)

    elif isinstance(desc, asdl.Sum) and asdl.is_simple(desc):
      # Encode enums as integers.  TODO later: Don't use 3 bytes!  Can use 1
      # byte for most enums.
      enc.Int(field_val.enum_id, this_chunk)

    # Write variable length field first, assuming that it's a ref/pointer.
    # TODO: allow one inline, hanging string or array per record.
    elif isinstance(desc, asdl.StrType):
      ref = out.Write(enc.PaddedStr(field_val))
      enc.Ref(ref, this_chunk)

    elif isinstance(desc, asdl.ArrayType):
      item_desc = desc.desc
      ref = EncodeArray(field_val, item_desc, enc, out)
      enc.Ref(ref, this_chunk)

    elif isinstance(desc, asdl.MaybeType):
      item_desc = desc.desc
      ok = False
      if isinstance(item_desc, asdl.Sum):
        if not asdl.is_simple(item_desc):
          ok = True
      elif isinstance(item_desc, asdl.Product):
        ok = True

      if not ok:
        raise AssertionError(
            "Currently not encoding simple optional types: %s", field_val)

      if field_val is None:
        enc.Ref(0, this_chunk)
      else:
        ref = EncodeObj(field_val, enc, out)
        enc.Ref(ref, this_chunk)

    else:
      # Recursive call for child records.  Write children before parents.
      ref = EncodeObj(field_val, enc, out)
      enc.Ref(ref, this_chunk)

  # Write the parent record
  this_ref = out.Write(enc.PaddedBlock(this_chunk))
  return this_ref


def EncodeRoot(obj, enc, out):
  ref = out.Write(b'OHP\x01')  # header, version 1
  assert ref == 0
  # 4-byte alignment, then 3 byte placeholder for the root ref.
  ref = out.Write(b'\4\0\0\0')
  assert ref == 1

  root_ref = EncodeObj(obj, enc, out)
  chunk = bytearray()
  enc.Ref(root_ref, chunk)
  out.WriteRootRef(chunk)

  #print("Root obj ref:", root_ref)
