#!/usr/bin/python
"""
runtime.py: Objects and types needed at runtime.

asdl/front_end.py and asdl/asdl_.py should not be shipped with the binary.
They are only needed for the gen_python.py compiler.
"""
from __future__ import print_function

import posix

from core import util


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


def _CheckType(value, expected_desc):
  """Is value of type expected_desc?

  Args:
    value: Obj or primitive type
    expected_desc: IntType, ArrayType, MaybeType, CompoundType, etc.
  """
  if isinstance(expected_desc, MaybeType):
    if value is None:
      return True
    return _CheckType(value, expected_desc.desc)

  if isinstance(expected_desc, ArrayType):
    if not isinstance(value, list):
      return False
    # Now check all entries
    for item in value:
      # Hm this is a hack that is necessary for the representation of arrays.
      if item is None:
        continue
      if not _CheckType(item, expected_desc.desc):
        return False
    return True

  if isinstance(expected_desc, StrType):
    return isinstance(value, str)

  if isinstance(expected_desc, IntType):
    return isinstance(value, int)

  if isinstance(expected_desc, BoolType):
    return isinstance(value, bool)

  if isinstance(expected_desc, UserType):
    return isinstance(value, expected_desc.typ)

  try:
    actual_desc = value.__class__.ASDL_TYPE
  except AttributeError:
    return False  # it's not of the right type

  if isinstance(expected_desc, CompoundType):
    return actual_desc is expected_desc

  if isinstance(expected_desc, SumType):
    #log("SumType expected desc %s", expected_desc)
    #log("SumType actual desc %s", actual_desc)
    if expected_desc.is_simple:
      # This is difference because of the way SimpleObj is used.
      return actual_desc is expected_desc
    else:
      # It has to be one of the alternatives
      for cons in expected_desc.cases:
        #log("CHECKING actual desc %s against %s" % (actual_desc, cons))
        if actual_desc is cons:
          return True
      return False

  raise AssertionError(
      'Invalid descriptor %r: %r' % (expected_desc.__class__, expected_desc))


class Obj(object):
  # NOTE: We're using CAPS for these static fields, since they are constant at
  # runtime after metaprogramming.
  ASDL_TYPE = None  # Used for type checking


class SimpleObj(Obj):
  """Base type of simple sum types."""
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
  """Base type of product types and compound sum types.

  Its ASDL_TYPE attribute should be runtime.CompoundType().
  """
  # TODO: Remove tag?  Or make it 0 by default for type checking.
  # The tag is always set for constructor types, which are subclasses of sum
  # types.  Never set for product types.
  tag = None

  def PrettyTree(self):
    """Return a homogeneous tree for pretty printing.

    By default, we use ASDL reflection, using ASDL_TYPE.GetFields().  But
    generated code can override to avoid this.
    """
    return fmt.MakePrettyTree(self)  # No abbreviation

  def __repr__(self):
    # TODO: Break this circular dependency.
    from asdl import format as fmt

    ast_f = fmt.TextOutput(util.Buffer())  # No color by default.
    tree = self.PrettyTree()
    fmt.PrintTree(tree, ast_f)
    s, _ = ast_f.GetRaw()
    return s

  # NOTE: ASDL_TYPE_CHECK=1 will be set for unit, spec, gold, wild tests, etc.
  # On benchmarks and in production it can be off.
  if posix.environ.get('ASDL_TYPE_CHECK'):
    def __setattr__(self, name, value):
      # None always OK for now?  Or should we have an asdl.UNDEF?
      if value is not None:
        expected = self.ASDL_TYPE.LookupFieldType(name)

        #log('expected type %s for field %s', expected, name)

        if not _CheckType(value, expected):
          raise TypeError("Field %r should be of type %s, got %r (%s)" %
                          (name, expected, value, value.__class__))
        global NUM_TYPE_CHECKS
        NUM_TYPE_CHECKS += 1
        
        #log('set %s = %r', name, value)

      # This is the way to do it for new-style calsses!
      # https://stackoverflow.com/questions/7042152/how-do-i-properly-override-setattr-and-getattribute-on-new-style-classes
      Obj.__setattr__(self, name, value)


# Other possible dynamic checking:
# - CheckUnassigned in the constructor?  Fields should be all initialized or
# none.
# - Maybe spids should never be mutated?  It can only be appended to?
# - SimpleObj could deny all __setattr__?
