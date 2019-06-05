"""
runtime.py: Objects and types needed at runtime.

asdl/front_end.py and asdl/asdl_.py should not be shipped with the binary.
They are only needed for the gen_python.py compiler.
"""
from __future__ import print_function

#import posix

import cStringIO
Buffer = cStringIO.StringIO


# Type Descriptors
#
# These are more convenient than using the AST directly, since it still has
# string type names?
#
# Although we share Product and Sum.

class _RuntimeType(object):
  """A node hierarchy that exists at runtime."""
  pass


class StrType(_RuntimeType):
  def __repr__(self):
    return '<Str>'


class IntType(_RuntimeType):
  def __repr__(self):
    return '<Int>'


class BoolType(_RuntimeType):
  def __repr__(self):
    return '<Bool>'


class DictType(_RuntimeType):
  def __repr__(self):
    return '<Dict>'


class ArrayType(_RuntimeType):
  def __init__(self, desc):
    self.desc = desc

  def __repr__(self):
    return '<Array %s>' % self.desc


class MaybeType(_RuntimeType):
  def __init__(self, desc):
    self.desc = desc  # another descriptor

  def __repr__(self):
    return '<Maybe %s>' % self.desc


class UserType(_RuntimeType):
  def __init__(self, typ):
    assert isinstance(typ, type), typ
    self.typ = typ

  def __repr__(self):
    return '<UserType %s>' % self.typ


class SumType(_RuntimeType):
  """Dummy node that doesn't require any reflection.

  obj.ASDL_TYPE points directly to the constructor, which you reflect on.
  """
  def __init__(self, is_simple):
    self.is_simple = is_simple  # for type checking
    self.cases = []  # list of _RuntimeType for type checking

  def __repr__(self):
    # We need an entry for this but we don't use it?
    return '<SumType with %d cases at %d>' % (
        len(self.cases), id(self))


class CompoundType(_RuntimeType):
  """A product or Constructor instance.  Both have fields."""
  def __init__(self, fields):
    # List of (name, _RuntimeType) tuples.
    # NOTE: This list may be mutated after its set.
    self.fields = fields

  def __repr__(self):
    return '<CompoundType %s>' % self.fields

  def GetFieldNames(self):
    for field_name, _ in self.fields:
      yield field_name

  def GetFields(self):
    for field_name, descriptor in self.fields:
      yield field_name, descriptor

  def LookupFieldType(self, field_name):
    """
    NOTE: Only used by py_meta.py.
    """
    for n, descriptor in self.fields:
      if n == field_name:
        return descriptor
    raise TypeError('Invalid field %r' % field_name)


BUILTIN_TYPES = {
    'string': StrType(),
    'int': IntType(),
    'bool': BoolType(),
    'dict': DictType(),
}




class Obj(object):
  # NOTE: We're using CAPS for these static fields, since they are constant at
  # runtime after metaprogramming.
  ASDL_TYPE = None  # Used for type checking


class SimpleObj(Obj):
  """An enum value.

  Other simple objects: int, str, maybe later a float.
  """
  def __init__(self, enum_id, name):
    self.enum_id = enum_id
    self.name = name

  # TODO: Why is __hash__ needed?  Otherwise native/fastlex_test.py fails.
  # util.Enum required it too.  I thought that instances would hash by
  # identity?
  #
  # Example:
  # class bool_arg_type_e(py_meta.SimpleObj):
  #   ASDL_TYPE = TYPE_LOOKUP['bool_arg_type']
  # bool_arg_type_e.Undefined = bool_arg_type_e(1, 'Undefined')

  def __hash__(self):
    # Could it be the integer self.enum_id?
    return hash(self.__class__.__name__ + self.name)

  def __repr__(self):
    return '<%s %s %s>' % (self.__class__.__name__, self.name, self.enum_id)


NUM_TYPE_CHECKS = 0

class CompoundObj(Obj):
  # TODO: Remove tag?
  # The tag is always set for constructor types, which are subclasses of sum
  # types.  Never set for product types.
  tag = None


# Other possible dynamic checking:
# - CheckUnassigned in the constructor?  Fields should be all initialized or
# none.
# - Maybe spids should never be mutated?  It can only be appended to?
# - SimpleObj could deny all __setattr__?
