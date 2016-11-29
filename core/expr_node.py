#!/usr/bin/python
"""
arith_node.py - AST nodes for arithmetic expressions
"""

import sys

from core.base import _Node
from core.id_kind import IdName, Id


class _ExprNode(_Node):
  """Abstract base class for internal nodes of a $(()) expression.

  It is an AstNode because it has tokens/words to point to?
  """
  def __init__(self, id):
    _Node.__init__(self, id)

  def PrintLine(self, f):
    raise NotImplementedError


# NOTE: Like VarSubPart, but without any ops.
class VarExprNode(_ExprNode):
  def __init__(self, var_name):
    _ExprNode.__init__(self, Id.Node_ArithVar)
    self.var_name = var_name  # type: str

  def PrintLine(self, f):
    f.write('(VarExprNode %s)' % self.var_name)


class UnaryExprNode(_ExprNode):
  """
  Arith: ~ - etc.

  Boolean:
      -z -n hold a Word; ! holds another _BNode; butI think we are just
      treating them all as _Node
  """
  def __init__(self, op_id, child):
    _ExprNode.__init__(self, Id.Node_UnaryExpr)
    self.op_id = op_id
    self.child = child  # type: _ExprNode

  def PrintLine(self, f):
    f.write('(%s %s)' % (IdName(self.op_id), self.child))


class BinaryExprNode(_ExprNode):
  """
  Arith: + / < etc>

  Boolean:

  ==, == as a GLOB with RHS detected at parse time, -gt for integers, -ot for
  files

  && and || hold a pair of _BNode instances.
  """
  def __init__(self, op_id, left, right):
    _ExprNode.__init__(self, Id.Node_BinaryExpr)
    self.op_id = op_id
    self.left = left
    self.right = right

  def PrintLine(self, f):
    f.write('(%s %s %s)' % (IdName(self.op_id), self.left, self.right))


class TernaryExprNode(_ExprNode):
  """
  For b ? true : false
  """
  def __init__(self, op_id, cond, true_expr, false_expr):
    _ExprNode.__init__(self, Id.Node_TernaryExpr)
    # NOTE: We might use this for PatSub and slice, so keep a_Id.
    self.op_id = op_id
    self.cond = cond  # type: _ExprNode
    self.true_expr = true_expr  # type: _ExprNode
    self.false_expr = false_expr  # type: _ExprNode

  def PrintLine(self, f):
    f.write('(%s %s %s %s)' % (
        IdName(self.op_id), self.cond, self.true_expr, self.false_expr))
