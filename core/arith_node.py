#!/usr/bin/python
"""
arith_node.py - AST nodes for arithmetic expressions
"""

import sys

from core.base import _Node
from core.id_kind import IdName, Id


class _ANode(_Node):
  """Abstract base class for internal nodes of a $(()) expression.

  It is an AstNode because it has tokens/words to point to?
  """
  def __init__(self, atype):
    _Node.__init__(self, 'TODO: get rid of')
    self.atype = atype  # type: TN

  def PrintLine(self, f):
    raise NotImplementedError


class UnaryANode(_ANode):
  """
  For ~ - etc.
  """
  def __init__(self, atype, child):
    _ANode.__init__(self, atype)
    self.child = child  # type: _ANode

  def PrintLine(self, f):
    f.write('{A1 ')
    f.write('%s %s ' % (IdName(self.atype), self.child))
    f.write('}')


class BinaryANode(_ANode):
  """
  For + / < etc>
  """
  def __init__(self, atype, left, right):
    _ANode.__init__(self, atype)
    self.left = left
    self.right = right

  def PrintLine(self, f):
    f.write('{A2 ')
    f.write('%s %s %s' % (IdName(self.atype), self.left,
        self.right))
    f.write('}')


class TernaryANode(_ANode):
  """
  For b ? true : false
  """
  def __init__(self, atype, cond, true_expr, false_expr):
    _ANode.__init__(self, atype)
    self.cond = cond  # type: _ANode
    self.true_expr = true_expr  # type: _ANode
    self.false_expr = false_expr  # type: _ANode

  def PrintLine(self, f):
    f.write('{A3 ')
    f.write('%s %s %s %s' % (IdName(self.atype), self.cond,
        self.true_expr, self.false_expr))
    f.write('}')


class AtomANode(_ANode):
  """
  For a token like .
  This could be LiteralWord too, but it's not worth it
  """
  def __init__(self, word):
    _ANode.__init__(self, Id.Word_Compound)
    self.word = word  # type: Word

  def PrintLine(self, f):
    f.write('{A Atom ')
    f.write('%s %s' % (IdName(self.atype), self.word))
    f.write('}')
