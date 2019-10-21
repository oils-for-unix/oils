#!/usr/bin/env python2
"""
pybase.py
"""
from __future__ import print_function

from mycpp import mylib

from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.hnode_asdl import hnode_t


class Obj(object):
  # NOTE: We're using CAPS for these static fields, since they are constant at
  # runtime after metaprogramming.
  ASDL_TYPE = None  # Used for type checking


class SimpleObj(int):
  """Base type of simple sum types."""
  # TODO: Get rid of this indirection?  Although mycpp might use it.
  pass


class CompoundObj(Obj):
  # TODO: Remove tag?
  # The tag is always set for constructor types, which are subclasses of sum
  # types.  Never set for product types.
  tag = 0  # TYPED: Changed from None.  0 is invalid!

  def PrettyTree(self):
    # type: () -> hnode_t
    raise NotImplementedError(self.__class__.__name__)

  def _AbbreviatedTree(self):
    # type: () -> hnode_t
    raise NotImplementedError(self.__class__.__name__)

  def AbbreviatedTree(self):
    # type: () -> hnode_t
    raise NotImplementedError(self.__class__.__name__)

  def PrettyPrint(self, f=None):
    # type: (Optional[mylib.Writer]) -> None
    """Print abbreviated tree in color, for debugging."""
    from asdl import format as fmt
    f = f if f else mylib.Stdout()

    ast_f = fmt.DetectConsoleOutput(f)
    tree = self.AbbreviatedTree()
    fmt.PrintTree(tree, ast_f)

  def __repr__(self):
    # type: () -> str
    # TODO: Break this circular dependency.
    from asdl import format as fmt

    ast_f = fmt.TextOutput(mylib.BufWriter())  # No color by default.
    tree = self.PrettyTree()
    fmt.PrintTree(tree, ast_f)
    s, _ = ast_f.GetRaw()
    return s
