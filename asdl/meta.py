"""
meta.py
"""
from __future__ import print_function

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
  def __init__(self, mod_name, type_name):
    #assert isinstance(typ, type), typ
    self.mod_name = mod_name
    self.type_name = type_name

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


# TODO: Delete some of these methods!

class CompoundType(_RuntimeType):
  """A product or Constructor instance.  Both have fields."""
  def __init__(self, fields):
    # List of (name, _RuntimeType) tuples.
    # NOTE: This list may be mutated after initialization.
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
    """Get the type descriptor for a field."""
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

