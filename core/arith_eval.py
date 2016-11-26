#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
arith_eval.py

TODO: Turn it into a class
"""

import sys

from core.id_kind import Id
from core.arith_node import _ANode, TernaryANode
from core.util import cast

#from core import word_eval 


class ArithEvalError(RuntimeError): pass

# In C++ is there a compact notation for {true, i+i}?  ArithEvalResult,
# BoolEvalResult, CmdExecResult?  Word is handled differntly because it's a
# string.

class ArithEvaluator:
  def __init__(self, ev):
    self.ev = ev  # type: word_eval.WordEvaluator
    self.result = 0

  def Result(self):
    return self.result

  def Eval(self, node: _ANode):
    try:
      result = self._Eval(node)
    except RuntimeError:
      ok = False
    else:
      ok = True
      self.result = result
    return ok

  def _Eval(self, node: _ANode):
    """
    Args:
      node: _ANode

    Issue: Word is not a kind of _ANode or ExprNode.  It is a _Node however,
    because it has an Id type.

    TODO:
    - Error checking.  The return value should probably be success/fail, or
      cflow, and then the integer result can be ArithEval.Result()
    """
    atype = node.atype

    if atype == Id.Arith_QMark:
      node = cast(TernaryANode, node)

      lhs = self._Eval(node.cond)
      if lhs != 0:
        ret = self._Eval(node.true_expr)
      else:
        ret = self._Eval(node.false_expr)
      return ret

    # TODO: Should we come up with a kind/arity??
    elif atype == Id.Node_UnaryPlus:
      return self._Eval(node.child)

    elif atype == Id.Node_UnaryMinus:
      return -self._Eval(node.child)

    elif atype == Id.Word_Compound:
      ok, i = self.ev.ArithEvalWord(node.word)
      if ok:
        return i
      else:
        raise ArithEvalError(self.ev.Error())

    # op precedence is used during parsing, op arity is used during execution.
    else:

      # TODO: Do type check at PARSE TIME, where applicable
      lhs = self._Eval(node.left)
      rhs = self._Eval(node.right)

      if atype == Id.Arith_Comma:
        return rhs

      # For now:
      if atype == Id.Arith_Plus:
        return lhs + rhs
      if atype == Id.Arith_Minus:
        return lhs - rhs

      if atype == Id.Arith_Star:
        return lhs * rhs
      if atype == Id.Arith_Slash:
        return lhs / rhs
      if atype == Id.Arith_Percent:
        return lhs % rhs

      if atype == Id.Arith_DStar:
        return lhs ** rhs

    raise NotImplementedError
