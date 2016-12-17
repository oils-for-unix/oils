#!/usr/bin/env python3
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
expr_eval.py -- Currently used for boolean and arithmetic expressions.
"""

import os

try:
  from core import libc
except ImportError:
  from core import fake_libc as libc

from core.expr_node import _ExprNode, TernaryExprNode
from core.id_kind import BOOL_OPS, OperandType, Id, IdName
from core.util import cast
from core.util import log
from core.value import TValue

#from core import word_eval


class ExprEvalError(RuntimeError): pass

# In C++ is there a compact notation for {true, i+i}?  ArithEvalResult,
# BoolEvalResult, CmdExecResult?  Word is handled differntly because it's a
# string.


class ExprEvaluator:
  """
  For now the arith and bool evaluators share some logic.
  """

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

  def Eval(self, node: _ExprNode):
    try:
      result = self._Eval(node)
    except ExprEvalError as e:
      self._AddErrorContext(str(e))
      ok = False
    else:
      self.result = result
      ok = True
    return ok


class ArithEvaluator(ExprEvaluator):

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

  def _Eval(self, node: _ExprNode):
    """
    Args:
      node: _ExprNode

    Issue: Word is not a kind of _ExprNode or ExprNode.  It is a _Node however,
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
        raise ExprEvalError()

    elif node.id == Id.Word_Compound:  # constant string
      ok, val = self.word_ev.EvalCompoundWord(node, elide_empty=False)
      if not ok:
        raise ExprEvalError(self.word_ev.Error())

      ok, i = self._ValToInteger(val)
      if ok:
        return i
      else:
        raise ExprEvalError()

    elif node.id == Id.Node_UnaryExpr:
      atype = node.op_id

      # TODO: Should we come up with a kind/arity??
      if atype == Id.Node_UnaryPlus:
        return self._Eval(node.child)

      elif atype == Id.Node_UnaryMinus:
        return -self._Eval(node.child)

    elif node.id == Id.Node_TernaryExpr:
      if node.op_id == Id.Arith_QMark:
        node = cast(TernaryExprNode, node)

        lhs = self._Eval(node.cond)
        if lhs != 0:
          ret = self._Eval(node.true_expr)
        else:
          ret = self._Eval(node.false_expr)
        return ret
      else:
        raise ExprEvalError("%s not implemented" % IdName(node.op_id))

    elif node.id == Id.Node_BinaryExpr:
      # TODO: Do type check at PARSE TIME, where applicable
      lhs = self._Eval(node.left)
      rhs = self._Eval(node.right)

      atype = node.op_id

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


# NOTE: Not used now
def _ValuesAreEqual(x, y):
  """Equality is used for [[.

  NOTE: Equality of arrays works!
  """
  if x.type != y.type:
    # TODO: should we throw an INCOMPARABLE error?  Same with -eq on strings.
    return False

  if x.type == TValue.STRING:
    #return x.s == y.s
    # RHS is the PATTERN.  LHS is the value.
    return libc.fnmatch(y.s, x.s)

  raise NotImplementedError


class BoolEvaluator(ExprEvaluator):

  def _SetRegexMatches(self, matches):
    """For ~= to set the BASH_REMATCH array."""
    self.mem

  def _EvalCompoundWord(self, word, do_glob=False):
    """
    Args:
      node: Id.Word_Compound
      do_glob: TOOD: rename this
    """
    ok, val = self.word_ev.EvalCompoundWord(word, do_glob=do_glob,
                                            elide_empty=False)
    if not ok:
      raise ExprEvalError(self.word_ev.Error())

    is_str, s = val.AsString()
    if not is_str:
      raise ExprEvaluator("Expected string, got array")

    return s

  def _Eval(self, node):
    # TODO: Switch on node.tag.
    if node.id == Id.Word_Compound:
      s = self._EvalCompoundWord(node)
      return bool(s)

    if node.id == Id.Node_UnaryExpr:
      op_id = node.op_id
      if op_id == Id.KW_Bang:
        # child could either be a Word, or it could be a BNode
        b = self._Eval(node.child)
        return not b

      s = self._EvalCompoundWord(node.child)

      # Now dispatch on arg type
      arg_type = BOOL_OPS[op_id]
      if arg_type == OperandType.Path:
        try:
          mode = os.stat(s).st_mode
        except FileNotFoundError as e:
          # TODO: Signal extra debug information?
          #self._AddErrorContext("Error from stat(%r): %s" % (s, e))
          return False

        if op_id == Id.BoolUnary_f:
          return stat.S_ISREG(mode)

      if arg_type == OperandType.Str:
        if op_id == Id.BoolUnary_z:
          return not bool(s)
        if op_id == Id.BoolUnary_n:
          return bool(s)

        raise NotImplementedError(op_id)

      raise NotImplementedError(arg_type)

    if node.id == Id.Node_BinaryExpr:
      op_id = node.op_id

      # Short-circuit evaluation
      if op_id == Id.Op_DAmp:
        if self._Eval(node.left):
          return self._Eval(node.right)
        else:
          return False

      if op_id == Id.Op_DPipe:
        if self._Eval(node.left):
          return True
        else:
          return self._Eval(node.right)

      s1 = self._EvalCompoundWord(node.left)
      # Whehter to glob escape
      do_glob = op_id in (
          Id.BoolBinary_Equal, Id.BoolBinary_DEqual, Id.BoolBinary_NEqual)
      s2 = self._EvalCompoundWord(node.right, do_glob=do_glob)

      # Now dispatch on arg type
      arg_type = BOOL_OPS[op_id]

      if arg_type == OperandType.Path:
        st1 = os.stat(s1)
        st2 = os.stat(s2)

        if op_id == Id.BoolBinary_nt:
          return True  # TODO: test newer than (mtime)

      if arg_type == OperandType.Int:
        try:
          i1 = int(s1)
          i2 = int(s2)
        except ValueError as e:
          # NOTE: Bash turns these into zero, but we won't by default.  Could
          # provide a compat option.
          # Also I think this should turn into exit code 3:
          # - 0 true / 1 false / 3 runtime error
          # - 2 is for PARSE error.
          raise ExprEvalError("Invalid integer: %s" % e)

        if op_id == Id.BoolBinary_eq:
          return i1 == i2
        if op_id == Id.BoolBinary_ne:
          return i1 != i2

        raise NotImplementedError(op_id)

      if arg_type == OperandType.Str:
        # TODO:
        # - Compare arrays.  (Although bash coerces them to string first)

        if op_id in (Id.BoolBinary_Equal, Id.BoolBinary_DEqual):
          #return True, _ValuesAreEqual(val1, val2)
          return libc.fnmatch(s2, s1)

        if op_id == Id.BoolBinary_NEqual:
          #return True, not _ValuesAreEqual(val1, val2)
          return not libc.fnmatch(s2, s1)

        if op_id == Id.BoolBinary_EqualTilde:
          # NOTE: regex matching can't fail if compilation succeeds.
          match = libc.regex_match(s2, s1)
          # TODO: BASH_REMATCH or REGEX_MATCH
          if match == 1:
            self._SetRegexMatches('TODO')
            is_match = True
          elif match == 0:
            is_match = False
          elif match == -1:
            raise AssertionError(
                "Invalid regex %r: should have been caught at compile time" %
                s2)
          else:
            raise AssertionError

          return is_match

        if op_id == Id.Redir_Less:  # pun
          return s1 < s2

        if op_id == Id.Redir_Great:  # pun
          return s1 > s2

        raise NotImplementedError(op_id)

    # We could have govered all node IDs
    raise AssertionError(IdName(node.id))
