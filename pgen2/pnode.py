#!/usr/bin/env python2
"""
pnode.py
"""
from __future__ import print_function

from typing import TYPE_CHECKING, Optional, List

if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import Token


class PNode(object):
  __slots__ = ('typ', 'tok', 'children')

  def __init__(self, typ, tok, children):
    # type: (int, Optional[Token], Optional[List[PNode]]) -> None
    self.typ = typ  # token or non-terminal
    self.tok = tok  # In Oil, this is syntax_asdl.Token.  In OPy, it's a
                    # 3-tuple (val, prefix, loc)
                    # NOTE: This is None for the first entry in the stack?
    self.children = children

  def __repr__(self):
    # type: () -> str
    tok_str = str(self.tok) if self.tok else '-'
    ch_str = 'with %d children' % len(self.children) \
        if self.children is not None else ''
    return '(PNode %s %s %s)' % (self.typ, tok_str, ch_str)

  def AddChild(self, node):
    # type: (PNode) -> None
    """
    Add `node` as a child.
    """
    self.children.append(node)

  def GetChild(self, i):
    # type: (int) -> PNode
    """
    Returns the `i`th uncomsumed child.
    """
    if i < 0:
      return self.children[i]

    return self.children[i]

  def NumChildren(self):
    # type: () -> int
    """
    Returns the number of unconsumed children.
    """
    return len(self.children)


class PNodeAllocator(object):
  def __init__(self):
    # type: () -> None
    return

  def NewPNode(self, typ, tok):
    # type: (int, Optional[Token]) -> PNode
    return PNode(typ, tok, [])

  def Clear(self):
    # type: () -> None
    return
