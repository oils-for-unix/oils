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


#
# BNode
#

class _BNode(_Node):
  """Abstract base class for internal nodes of a [[ expresion.

  It is an _Node because it has tokens/words to point to?

  TODO: Change this to ExprNode, and use op_id instead of a_id and b_id.
  """
  def __init__(self, id, b_id):
    _Node.__init__(self, id)
    self.b_id = b_id

  def PrintLine(self, f):
    raise NotImplementedError  # Abstract


class UnaryBNode(_BNode):
  """
  -z -n hold a Word; ! holds another _BNode; butI think we are just treating
  them all as _Node
  """
  def __init__(self, b_id, child):
    _BNode.__init__(self, Id.Node_UnaryExpr, b_id)
    self.child = child  # type: _Node

  def PrintLine(self, f):
    f.write('{B1 ')
    f.write('%s %s' % (IdName(self.b_id), self.child))
    f.write('}')


class BinaryBNode(_BNode):
  """
  ==, == as a GLOB with RHS detected at parse time, -gt for integers, -ot for
  files

  && and || hold a pair of _BNode instances.
  """
  def __init__(self, b_id, left, right):
    _BNode.__init__(self, Id.Node_BinaryExpr, b_id)
    self.left = left  # type: _Node
    self.right = right  # type: _Node

  def PrintLine(self, f):
    f.write('{B2 ')
    f.write('%s %s %s' % (IdName(self.b_id), self.left, self.right))
    f.write('}')
