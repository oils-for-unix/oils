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

from core.id_kind import Id, IdName
from core.arith_node import _ANode, TernaryANode
from core.util import cast

#from core import word_eval 


class ArithEvalError(RuntimeError): pass

# In C++ is there a compact notation for {true, i+i}?  ArithEvalResult,
# BoolEvalResult, CmdExecResult?  Word is handled differntly because it's a
# string.

class ArithEvaluator:

  def __init__(self, mem, word_ev):
    self.mem = mem
    self.word_ev = word_ev  # type: word_eval.WordEvaluator
    self.result = 0
    self.error_stack = []

  def _AddErrorContext(self, msg, *args):
    if msg:
      msg = msg % args
    self.error_stack.append(msg)

  def Error(self):
    return self.error_stack

  def Result(self):
    return self.result

  def Eval(self, node: _ANode):
    try:
      result = self._Eval(node)
    except ArithEvalError as e:
      self._AddErrorContext(e.args[0])
      ok = False
    else:
      self.result = result
      ok = True
    return ok

  def _ValToInteger(self, val):
    """Evaluate with the rules of arithmetic expressions.

    Dumb stuff like $(( $(echo 1)$(echo 2) + 1 ))  =>  13  is possible.

    0xAB -- hex constant
    010 -- octable constant
    64#z -- arbitary base constant
    bare word: variable
    quoted word: string
    """
    is_str, s = val.AsString()
    if not is_str:
      # TODO: Error message: expected string but got integer/array
      return False, 0

    if s.startswith('0x'):
      try:
        integer = int(s, 16)
      except ValueError:
        # TODO: Show line number
        self._AddErrorContext('Invalid hex constant %r' % s)
        return False, 0
      return True, integer

    if s.startswith('0'):
      try:
        integer = int(s, 8)
      except ValueError:
        # TODO: Show line number
        self._AddErrorContext('Invalid octal constant %r' % s)
        return False, 0
      return True, integer

    if '#' in s:
      b, digits = s.split('#', 1)
      try:
        base = int(b)
      except ValueError:
        self._AddErrorContext('Invalid base for numeric constant %r' % b)
        return False, 0

      integer = 0
      n = 1
      for char in digits:
        if 'a' <= char and char <= 'z':
          digit = ord(char) - ord('a') + 10
        elif 'A' <= char and char <= 'Z':
          digit = ord(char) - ord('A') + 36
        elif char == '@':  # horrible syntax
          digit = 62
        elif char == '_':
          digit = 63
        elif char.isdigit():
          digit = int(char)
        else:
          self._AddErrorContext('Invalid digits for numeric constant %r' % digits)
          return False, 0

        integer += digit * n
        n *= base
      return True, integer

    # Plain integer
    try:
      integer = int(s)
    except ValueError:
      self._AddErrorContext("Invalid integer constant %r" % s)
      return False, 0
    return True, integer

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
    # NOTE: Variable NAMES cannot be formed dynamically; but INTEGERS can.
    # ${foo:-3}4 is OK.  $? will be a compound word too, so we don't have to
    # handle that as a special case.
    if node.id == Id.Node_ArithVar:
      defined, val = self.mem.Get(node.var_name)
      # By default, undefined variables are the ZERO value.  TODO: Respect
      # nounset and raise an exception.
      if not defined:
        return 0

      ok, i = self._ValToInteger(val)
      if ok:
        return i
      else:
        raise ArithEvalError()

    elif node.id == Id.Word_Compound:  # constant string
      ok, val = self.word_ev.EvalCompoundWord(node, elide_empty=False)
      if not ok:
        raise ArithEvalError(self.word_ev.Error())

      ok, i = self._ValToInteger(val)
      if ok:
        return i
      else:
        raise ArithEvalError()

    elif node.id == Id.Node_UnaryExpr:
      atype = node.a_id

      # TODO: Should we come up with a kind/arity??
      if atype == Id.Node_UnaryPlus:
        return self._Eval(node.child)

      elif atype == Id.Node_UnaryMinus:
        return -self._Eval(node.child)

    elif node.id == Id.Node_TernaryExpr:
      if node.a_id == Id.Arith_QMark:
        node = cast(TernaryANode, node)

        lhs = self._Eval(node.cond)
        if lhs != 0:
          ret = self._Eval(node.true_expr)
        else:
          ret = self._Eval(node.false_expr)
        return ret
      else:
        raise ArithEvalError("%s not implemented" % IdName(node.a_id))

    elif node.id == Id.Node_BinaryExpr:
      # TODO: Do type check at PARSE TIME, where applicable
      lhs = self._Eval(node.left)
      rhs = self._Eval(node.right)

      atype = node.a_id

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

    else:
      raise AssertionError("Invalid node %r" % node.id)

    raise AssertionError("Shouldn't get here")
