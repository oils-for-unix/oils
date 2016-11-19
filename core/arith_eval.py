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

from core.tokens import *


def ArithEval(node, ev):
  """
  Args:
    node: _ANode

  TODO: Add errors
  """
  atype = node.atype

  if atype == AS_OP_QMARK:
    lhs = int(ArithEval(node.cond, ev))
    if lhs != 0:
      ret = int(ArithEval(node.true_expr, ev))
    else:
      ret = int(ArithEval(node.false_expr, ev))
    return ret

  # TODO: Should we come up with a kind/arity??
  elif atype == NODE_UNARY_PLUS:
    return int(ArithEval(node.child, ev))
  elif atype == NODE_UNARY_MINUS:
    return -int(ArithEval(node.child, ev))

  elif atype == NODE_ARITH_WORD:
    ok, i = ev.ArithEvalWord(node.word)
    #assert ok
    return i

  # op precedence is used during parsing, op arity is used during execution.
  else:

    # TODO: Do type check at PARSE TIME, where applicable
    lhs = int(ArithEval(node.left, ev))
    rhs = int(ArithEval(node.right, ev))

    if atype == AS_OP_COMMA:
      return rhs

    # For now:
    if atype == AS_OP_PLUS:
      return lhs + rhs
    if atype == AS_OP_MINUS:
      return lhs - rhs

    if atype == AS_OP_STAR:
      return lhs * rhs
    if atype == AS_OP_SLASH:
      return lhs / rhs
    if atype == AS_OP_PERCENT:
      return lhs % rhs

    if atype == AS_OP_DSTAR:
      return lhs ** rhs

  raise NotImplementedError
