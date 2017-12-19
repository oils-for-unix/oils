#!/usr/bin/python
"""
asdl_base.py

Base classes for generated code.
"""
import io

from core import util


#
# COMPATIBLE GENERATED code
#


# Copied from py_meta
class Obj(object):
  # NOTE: We're using CAPS for these static fields, since they are constant at
  # runtime after metaprogramming.
  DESCRIPTOR = None  # Used for type checking


class SimpleObj(Obj):
  def __init__(self, enum_id, name):
    self.enum_id = enum_id
    self.name = name

  def __repr__(self):
    return '<%s %s %s>' % (self.__class__.__name__, self.name, self.enum_id)


class CompoundObj(Obj):
  FIELDS = []  # ordered list of field names, overriden
  DESCRIPTOR_LOOKUP = {}  # field name: (asdl.Sum | asdl.Product | ...)

  """
  def __repr__(self):
    # Breaking circular dependency, gah.
    from asdl import format as fmt

    ast_f = fmt.TextOutput(util.Buffer())  # No color by default.
    ast_f = fmt.AnsiOutput(io.StringIO())
    tree = fmt.MakeTree(self)
    fmt.PrintTree(tree, ast_f)
    s, _ = ast_f.GetRaw()
    return s
  """


#
# NEW metaprogramming API
#

# Copied from py_meta
class Obj2(object):
  ASDL_TYPE = None  # Used for type checking


# Do we need these?  I gues __repr__ is important.  But that can be generated
# then?  __init__ and __repr__ need to be generated.
# Or I guess __repr__ can always be fmt.PrintTree(...)?
# You are using this for enums too, so __repr__ has to be hooked up.

#class SimpleObj2(Obj2):
#  def __init__(self, enum_id, sum_type_name):
#    self.enum_id = enum_id
#    self.name = sum_type_name
#
#  def __repr__(self):
#    # NOTE: This be self.__bases__[0].__name__?  There's probably no advantage
#    # to that though?
#    return '<%s %s %s>' % (self.__class__.__name__, self.name, self.enum_id)


#class CompoundObj2(Obj2):
#  pass
