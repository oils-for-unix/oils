#!/usr/bin/python
"""
asdl_base.py

Base classes for generated code.
"""
import io

from core import util


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
