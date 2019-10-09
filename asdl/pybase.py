#!/usr/bin/env python2
"""
pybase.py
"""
from __future__ import print_function

import sys
from cStringIO import StringIO

from typing import IO

class Obj(object):
  # NOTE: We're using CAPS for these static fields, since they are constant at
  # runtime after metaprogramming.
  ASDL_TYPE = None  # Used for type checking


class SimpleObj(Obj):
  """Base type of simple sum types."""
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
  #   pass
  # bool_arg_type_e.Undefined = bool_arg_type_e(1, 'Undefined')

  def __hash__(self):
    # type: () -> int
    # Could it be the integer self.enum_id?
    return hash(self.__class__.__name__ + self.name)

  def __repr__(self):
    # type: () -> str
    return '<%s %s %s>' % (self.__class__.__name__, self.name, self.enum_id)


class CompoundObj(Obj):
  # TODO: Remove tag?
  # The tag is always set for constructor types, which are subclasses of sum
  # types.  Never set for product types.
  tag = 0  # TYPED: Changed from None.  0 is invalid!

  def PrettyTree(self):
    # type: () -> _PrettyBase
    raise NotImplementedError(self.__class__.__name__)

  def _AbbreviatedTree(self):
    # type: () -> _PrettyBase
    raise NotImplementedError(self.__class__.__name__)

  def AbbreviatedTree(self):
    # type: () -> _PrettyBase
    raise NotImplementedError(self.__class__.__name__)

  def PrettyPrint(self, f=sys.stdout):
    # type: (IO[str]) -> None
    """Print abbreviated tree in color, for debugging."""
    from asdl import format as fmt

    ast_f = fmt.DetectConsoleOutput(f)
    tree = self.AbbreviatedTree()
    fmt.PrintTree(tree, ast_f)

  def __repr__(self):
    # type: () -> str
    # TODO: Break this circular dependency.
    from asdl import format as fmt

    ast_f = fmt.TextOutput(StringIO())  # No color by default.
    tree = self.PrettyTree()
    fmt.PrintTree(tree, ast_f)
    s, _ = ast_f.GetRaw()
    return s
