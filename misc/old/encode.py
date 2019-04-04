"""
encode.py
"""

from asdl import asdl_ as asdl
from asdl import runtime
from asdl import const

from core import util


class EncodeError(Exception):
  def __init__(self, *args, **kwargs):
    Exception.__init__(self, *args, **kwargs)
    self.details_printed = False


_DEFAULT_ALIGNMENT = 4

class BinOutput(object):
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
    assert len(chunk) % self.alignment == 0
    self.f.write(chunk)

    ref = self.last_block
    num_blocks = len(chunk) // self.alignment  # int division
    #print('WROTE %d blocks' % num_blocks)
    self.last_block += num_blocks

    # Return a reference to the beginning
    return ref


class Params(object):
  """Encoding parameters.

  Hm most of these settings should be per-field, expressed in the schema.  The
  only global one is the ref/pointer alignment.  4 and 8 are the most likely
  choices, and 4 is probably fine, because you have 64 MB of addressable memory
  with 24 bit pointers.
  """

  def __init__(self, alignment=_DEFAULT_ALIGNMENT,
               int_width=const.DEFAULT_INT_WIDTH):
    self.alignment = alignment
    self.pointer_type = 'uint32_t'

    self.tag_width = 1  # for ArithVar vs ArithWord.
    self.int_width = int_width
    self.ref_width = int_width  # Constant 3, used by gen_cpp

    # used for fd, line/col
    # also I guess steuff like SimpleCommand
    self.index_width = 2  # 16 bits, e.g. max 64K entries in an array

    self.max_int = 1 << (self.int_width * 8)
    self.max_index = 1 << (self.index_width * 8)
    self.max_tag = 1 << (self.tag_width * 8)

  def Tag(self, i, chunk):
    if i > self.max_tag:
      raise AssertionError('Invalid id %r' % i)
    chunk.append(i & 0xFF)

  def Int(self, n, chunk):
    if n < 0:
      raise EncodeError(
          "ASDL can't currently encode negative numbers.  Got %d" % n)
    if n > self.max_int:
      raise EncodeError(
          '%d is too big to fit in %d bytes' % (n, self.int_width))

    for i in xrange(self.int_width):
      chunk.append(n & 0xFF)
      n >>= 8

  def Ref(self, n, chunk):
    # NOTE: ref width is currently the same as int width.  Could be different.
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
    chunk.extend(s)
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
      raise EncodeError("bytes object is too long (%d)" % n)
    for i in xrange(self.index_width):
      chunk.append(n & 0xFF)
      n >>= 8
    chunk.extend(buf)

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

  if isinstance(item_desc, asdl.IntType) or \
      isinstance(item_desc, asdl.BoolType):
    for item in obj_list:
      enc.Int(item, array_chunk)

  elif isinstance(item_desc, asdl.UserType):
    # Assume Id for now
    for item in obj_list:
      enc.Int(item.enum_value, array_chunk)

  elif isinstance(item_desc, asdl.StrType):
    for item in obj_list:
      ref = out.Write(enc.PaddedStr(item))
      enc.Ref(ref, array_chunk)

  elif isinstance(item_desc, asdl.Sum) and asdl.is_simple(item_desc):
    for item in obj_list:
      enc.Int(item.enum_id, array_chunk)

  else:
    # A simple value is either an int, enum, or pointer.  (Later: Iter<Str>
    # might be possible for locality.)
    assert \
        isinstance(item_desc, asdl.SumType) or \
        isinstance(item_desc, asdl.CompoundType), item_desc

    # This is like vector<T*>
    # Later:
    # - Product types can be put in line
    # - Sum types can even be put in line, if you have List<T> rather than
    # Array<T>.  Array implies O(1) random access; List doesn't.
    for item in obj_list:
      try:
        ref = EncodeObj(item, enc, out)
      except EncodeError as e:
        if not e.details_printed:
          util.log("Error encoding array: %s (item %s)", e, item)
          e.details_printed = True
        raise
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
  assert isinstance(obj, runtime.CompoundObj), \
    '%r is not a compound obj (%r)' % (obj, obj.__class__)

  # Constructor objects have a tag.
  if isinstance(obj.ASDL_TYPE, asdl.Constructor):
    enc.Tag(obj.tag, this_chunk)

  for name, desc in obj.ASDL_TYPE.GetFields():  # encode in order
    field_val = getattr(obj, name)

    # TODO:
    # - Float would be inline, etc.
    # - Repeated value: write them all adjacent to each other?

    is_maybe = False
    if isinstance(desc, asdl.MaybeType):
      is_maybe = True
      desc = desc.desc  # descent

    #
    # Now look at types
    #

    if isinstance(desc, asdl.IntType) or isinstance(desc, asdl.BoolType):
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

    elif isinstance(desc, asdl.UserType):
      if is_maybe and field_val is None:  # e.g. id? prefix_op
        enc.Ref(0, this_chunk)
      else:
        # Assume Id for now
        enc.Int(field_val.enum_value, this_chunk)

    else:
      if is_maybe and field_val is None:
        enc.Ref(0, this_chunk)
      else:
        try:
          ref = EncodeObj(field_val, enc, out)
        except EncodeError as e:
          if not e.details_printed:
            util.log("Error encoding %s : %s (val %s)", name, e, field_val)
            e.details_printed = True
          raise
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
  out.WriteRootRef(chunk)  # back up and write it

  #print("Root obj ref:", root_ref)
