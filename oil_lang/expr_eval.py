#!/usr/bin/env python2
"""
expr_eval.py
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import (
    expr_e, oil_word_part_e
)
from _devbuild.gen.runtime_asdl import (
    lvalue, value_e
)


class OilEvaluator(object):
  """Shared between arith and bool evaluators.

  They both:

  1. Convert strings to integers, respecting shopt -s strict_arith.
  2. Look up variables and evaluate words.
  """

  def __init__(self, mem, errfmt):
    self.mem = mem
    self.errfmt = errfmt

  def EvalLHS(self, node):
    if 0:
      print('EvalLHS()')
      node.PrettyPrint()
      print('')

    if node.tag == expr_e.Var:
      return lvalue.LhsName(node.name.val)
    else:
      # TODO:
      # subscripts, tuple unpacking, starred expressions, etc.

      raise NotImplementedError(node.__class__.__name__)

  def EvalWordPart(self, part):
    """
    TODO: We might not want oil_word_part_e?  Just use OSH word_part?
    """
    if part.tag == oil_word_part_e.Literal:
      return part.token.val

    raise NotImplementedError(part.__class__.__name__)

  def EvalRHS(self, node):
    """
    This is a naive PyObject evaluator!  It uses the type dispatch of the host
    Python interpreter.

    Returns:
      A Python object of ANY type.  Should be wrapped in value.Obj() for
      storing in Mem.
    """
    if 0:
      print('EvalRHS()')
      node.PrettyPrint()
      print('')

    if node.tag == expr_e.Const:
      return int(node.c.val)

    if node.tag == expr_e.Var:
      val = self.mem.GetVar(node.name.val)
      if val.tag == value_e.Undef:
        # TODO: e_die with token
        raise NameError('undefined')
      if val.tag == value_e.Str:
        return val.s
      if val.tag == value_e.StrArray:
        return val.strs  # node: has None
      if val.tag == value_e.AssocArray:
        return val.d
      if val.tag == value_e.Obj:
        return val.obj

    if node.tag == expr_e.DoubleQuoted:
      s = ''.join(self.EvalWordPart(part) for part in node.parts)
      return s

    if node.tag == expr_e.Binary:
      left = self.EvalRHS(node.left)
      right = self.EvalRHS(node.right)

      if node.op.id == Id.Arith_Plus:
        return left + right

      if node.op.id == Id.Arith_Minus:
        return left - right

      if node.op.id == Id.Arith_Star:
        return left * right

      raise NotImplementedError(node.op.id)

    if node.tag == expr_e.List:
      return [self.EvalRHS(e) for e in node.elts]

    if node.tag == expr_e.Subscript:
      collection = self.EvalRHS(node.collection)

      # TODO: handle multiple indices like a[i, j]
      index = self.EvalRHS(node.indices[0])
      return collection[index]

    raise NotImplementedError(node.__class__.__name__)
