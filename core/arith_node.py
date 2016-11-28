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
  def __init__(self, id):
    _Node.__init__(self, id)

  def PrintLine(self, f):
    raise NotImplementedError


# NOTE: Like VarSubPart, but without any ops.
class VarANode(_ANode):
  def __init__(self, var_name):
    _ANode.__init__(self, Id.Node_ArithVar)
    self.var_name = var_name  # type: str

  def PrintLine(self, f):
    f.write('{VarANode %s}' % self.var_name)


class UnaryANode(_ANode):
  """
  For ~ - etc.
  """
  def __init__(self, a_id, child):
    _ANode.__init__(self, Id.Node_UnaryExpr)
    self.a_id = a_id
    self.child = child  # type: _ANode

  def PrintLine(self, f):
    f.write('{A1 ')
    f.write('%s %s ' % (IdName(self.a_id), self.child))
    f.write('}')


class BinaryANode(_ANode):
  """
  For + / < etc>
  """
  def __init__(self, a_id, left, right):
    _ANode.__init__(self, Id.Node_BinaryExpr)
    self.a_id = a_id
    self.left = left
    self.right = right

  def PrintLine(self, f):
    f.write('{A2 ')
    f.write('%s %s %s' % (IdName(self.a_id), self.left,
        self.right))
    f.write('}')


class TernaryANode(_ANode):
  """
  For b ? true : false
  """
  def __init__(self, a_id, cond, true_expr, false_expr):
    _ANode.__init__(self, Id.Node_TernaryExpr)
    # NOTE: We might use this for PatSub and slice, so keep a_Id.
    self.a_id = a_id
    self.cond = cond  # type: _ANode
    self.true_expr = true_expr  # type: _ANode
    self.false_expr = false_expr  # type: _ANode

  def PrintLine(self, f):
    f.write('{A3 ')
    f.write('%s %s %s %s' % (IdName(self.a_id), self.cond,
        self.true_expr, self.false_expr))
    f.write('}')
