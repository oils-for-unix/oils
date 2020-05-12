"""
meta.py
"""
from __future__ import print_function

# Type Descriptors.  This is like the AST with names resolved.

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


class FloatType(_RuntimeType):
  def __repr__(self):
    return '<Float>'


class BoolType(_RuntimeType):
  def __repr__(self):
    return '<Bool>'


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


class MapType(_RuntimeType):
  def __init__(self, k_desc, v_desc):
    self.k_desc = k_desc
    self.v_desc = v_desc

  def __repr__(self):
    return '<Map %s %s>' % (self.k_desc, self.v_desc)


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

    # NOTE: The list of fields is mutated after initialization.
    self.fields = fields

    # TODO:
    #
    # I think we can get rid of the whole _RuntimeType rigamarole?
    # As long as we check names, then we can just walk the AST in
    # gen_{cpp,python}.

    # We're already walking a MIX of the AST.

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


PRIMITIVE_TYPES = {
    'string': StrType(),
    'int': IntType(),
    'float': FloatType(),
    'bool': BoolType(),

    # 'any' is used:
    # - for value.Obj in the the Oil expression evaluator.  We're not doing any
    #   dynamic or static checking now.
    'any': AnyType(),
}
