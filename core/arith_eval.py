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

from core.tokens import Id


def ArithEval(node, ev):
  """
  Args:
    node: _ANode

  TODO: Add errors
  """
  atype = node.atype

  if atype == Id.Arith_QMark:
    lhs = int(ArithEval(node.cond, ev))
    if lhs != 0:
      ret = int(ArithEval(node.true_expr, ev))
    else:
      ret = int(ArithEval(node.false_expr, ev))
    return ret

  # TODO: Should we come up with a kind/arity??
  elif atype == Id.Node_UnaryPlus:
    return int(ArithEval(node.child, ev))
  elif atype == Id.Node_UnaryMinus:
    return -int(ArithEval(node.child, ev))

  elif atype == Id.Node_ArithWord:
    ok, i = ev.ArithEvalWord(node.word)
    #assert ok
    return i

  # op precedence is used during parsing, op arity is used during execution.
  else:

    # TODO: Do type check at PARSE TIME, where applicable
    lhs = int(ArithEval(node.left, ev))
    rhs = int(ArithEval(node.right, ev))

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
