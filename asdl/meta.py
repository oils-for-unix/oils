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


class AnyType(_RuntimeType):
  def __repr__(self):
    return '<Any>'


class StrType(_RuntimeType):
  def __repr__(self):
    return '<Str>'


class IntType(_RuntimeType):
  def __repr__(self):
    return '<Int>'


class BoolType(_RuntimeType):
  def __repr__(self):
    return '<Bool>'


class AssocType(_RuntimeType):
  def __repr__(self):
    return '<Assoc>'


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
    self.mod_name = mod_name
    self.type_name = type_name

  def __repr__(self):
    return '<UserType %s %s>' % (self.mod_name, self.type_name)


class SumType(_RuntimeType):
  """Dummy node that doesn't require any reflection.

  obj.ASDL_TYPE points directly to the constructor, which you reflect on.
  """
  def __init__(self, is_simple, simple_variants):
    self.is_simple = is_simple  # for type checking
    self.simple_variants = simple_variants  # list of strings
    self.cases = []  # TODO: This is obsolete?

  def __repr__(self):
    # We need an entry for this but we don't use it?
    if self.is_simple:
      variants_str = '%d simple variants' % len(self.simple_variants)
    else:
      variants_str = 'not simple'
    return '<SumType at %d (%s)>' % (id(self), variants_str)


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

    # 'any' is used:
    # - for value.Obj in the the Oil expression evaluator.  We're not doing any
    #   dynamic or static checking now.
    'any': AnyType(),

    # - for the dict in value.AssocArray.
    'assoc': AssocType(),
}

