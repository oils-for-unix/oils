#!/usr/bin/python
"""
typed_runtime.py
"""
from __future__ import print_function


class Obj(object):
  # NOTE: We're using CAPS for these static fields, since they are constant at
  # runtime after metaprogramming.
  ASDL_TYPE = None  # Used for type checking


class SimpleObj(Obj):
  """An enum value.

  Other simple objects: int, str, maybe later a float.
  """
  def __init__(self, enum_id, name):
    # type: (int, str) -> None
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
    # type: () -> int
    # Could it be the integer self.enum_id?
    return hash(self.__class__.__name__ + self.name)

  def __repr__(self):
    # type: () -> str
    return '<%s %s %s>' % (self.__class__.__name__, self.name, self.enum_id)


NUM_TYPE_CHECKS = 0

class CompoundObj(Obj):
  # TODO: Remove tag?
  # The tag is always set for constructor types, which are subclasses of sum
  # types.  Never set for product types.
  tag = 0  # TYPED: Changed from None.  0 is invalid!
