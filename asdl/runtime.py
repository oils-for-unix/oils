#!/usr/bin/python
"""
runtime.py

- Base classes for generated code
- Nodes for pretty printing
"""
from __future__ import print_function

from cStringIO import StringIO
import sys

from typing import List, Tuple, Optional, IO


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


#
# A Homogeneous Tree for Pretty Printing.
#


class _PrettyBase(object):
  pass


class PrettyNode(_PrettyBase):
  """Homogeneous node for pretty-printing."""

  def __init__(self, node_type=None):
    # type: (Optional[str]) -> None
    self.node_type = node_type or ''  # type: str
    # Gah this signature is complicated.
    # Probably should have _PrettyRepeated?
    self.fields = []  # type: List[Tuple[str, _PrettyBase]]

    # Custom hooks set abbrev = True and use the nodes below.
    self.abbrev = False
    self.left = '('
    self.right = ')'
    # Used by abbreviations
    self.unnamed_fields = []  # type: List[_PrettyBase]

  def __repr__(self):
    # type: () -> str
    return '<PrettyNode %s %s>' % (self.node_type, self.fields)


class PrettyArray(_PrettyBase):
  def __init__(self):
    # type: () -> None
    self.children = []  # type: List[_PrettyBase]

  def __repr__(self):
    # type: () -> str
    return '<PrettyArray %s>' % (self.children)


# Color token types
Color_TypeName = 1
Color_StringConst = 2
Color_OtherConst = 3  # Int and bool.  Green?
Color_UserType = 4  # UserType Id


class PrettyLeaf(_PrettyBase):
  """Colored string for pretty-printing."""

  def __init__(self, s, e_color):
    # type: (Optional[str], int) -> None
    assert isinstance(s, str), s
    self.s = s
    self.e_color = e_color

  def __repr__(self):
    # type: () -> str
    return '<PrettyLeaf %s %s>' % (self.s, self.e_color)
