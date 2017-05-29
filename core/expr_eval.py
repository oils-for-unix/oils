#!/usr/bin/python
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

import libc  # for fnmatch

from core.id_kind import BOOL_OPS, OperandType, Id, IdName
from core import util
from core import runtime

from osh import ast_ as ast

log = util.log
e_die = util.e_die

arith_expr_e = ast.arith_expr_e
bool_expr_e = ast.bool_expr_e  # used for dispatch
word_e = ast.word_e
part_value_e = runtime.part_value_e
value_e = runtime.value_e


def _StringToInteger(s, word=None):
  """Use bash-like rules to coerce a string to an integer.

  Supports hex, octal, etc.
  """
  if s.startswith('0x'):
    try:
      integer = int(s, 16)
    except ValueError:
      # TODO: Show line number
      e_die('Invalid hex constant %r', s, word=word)
    return integer

  if s.startswith('0'):
    try:
      integer = int(s, 8)
    except ValueError:
      e_die('Invalid octal constant %r', s, word=word)  # TODO: Show line number
    return integer

  if '#' in s:
    b, digits = s.split('#', 1)
    try:
      base = int(b)
    except ValueError:
      e_die('Invalid base for numeric constant %r',  b, word=word)

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
        e_die('Invalid digits for numeric constant %r', digits, word=word)

      if digit >= base:
        e_die('Digits %r out of range for base %d', digits, base, word=word)

      integer += digit * n
      n *= base
    return integer

  # Plain integer
  try:
    integer = int(s)
  except ValueError:
    e_die("Invalid integer constant %r", s, word=word)
  return integer


def _ValToInteger(val, word=None):
  """Evaluate with the rules of arithmetic expressions.

  Dumb stuff like $(( $(echo 1)$(echo 2) + 1 ))  =>  13  is possible.

  0xAB -- hex constant
  010 -- octable constant
  64#z -- arbitary base constant
  bare word: variable
  quoted word: string
  """
  assert isinstance(val, runtime.value), val
  if val.tag != value_e.Str:
    # TODO: Error message: expected string but got integer/array
    e_die('Expected string but got %r', val)
  return _StringToInteger(val.s, word=word)


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

  # TODO: Remove this
  def Eval(self, node):
    return self._Eval(node)


class ArithEvaluator(ExprEvaluator):

  def _Eval(self, node):
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
    #if node.id == Id.Node_ArithVar:
    if node.tag == arith_expr_e.RightVar:
      # TODO: need token
      val = self.mem.Get(node.name)
      # By default, undefined variables are the ZERO value.  TODO: Respect
      # nounset and raise an exception.
      if val.tag == value_e.Undef:
        return 0

      return _ValToInteger(val)

    elif node.tag == arith_expr_e.ArithWord:  # constant string
      val = self.word_ev.EvalWordToString(node.w)
      return _ValToInteger(val, word=node.w)

    #elif node.id == Id.Node_UnaryExpr:
    elif node.tag == arith_expr_e.ArithUnary:
      atype = node.op_id

      # TODO: Should we come up with a kind/arity??
      if atype == Id.Node_UnaryPlus:
        return self._Eval(node.child)

      elif atype == Id.Node_UnaryMinus:
        return -self._Eval(node.child)

    #elif node.id == Id.Node_TernaryExpr:
    elif node.tag == arith_expr_e.TernaryOp:
      lhs = self._Eval(node.cond)
      if lhs != 0:
        ret = self._Eval(node.true_expr)
      else:
        ret = self._Eval(node.false_expr)
      return ret

    #elif node.id == Id.Node_BinaryExpr:
    elif node.tag == arith_expr_e.ArithBinary:
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
        try:
          return lhs / rhs
        except ZeroDivisionError:
          # TODO: Instead of op_id, I should have the token
          # node.right.w crashes if it's not a constant!
          e_die('Divide by zero', word=node.right.w)

      if atype == Id.Arith_Percent:
        return lhs % rhs

      if atype == Id.Arith_DStar:
        return lhs ** rhs

    else:
      raise NotImplementedError("Unhandled node %r" % node.__class__.__name__)

    raise AssertionError("Shouldn't get here")


class BoolEvaluator(ExprEvaluator):

  def _SetRegexMatches(self, matches):
    """For ~= to set the BASH_REMATCH array."""
    self.mem

  def _EvalCompoundWord(self, word, do_fnmatch=False):
    """
    Args:
      node: Id.Word_Compound
    """
    val = self.word_ev.EvalWordToString(word, do_fnmatch=do_fnmatch)
    return val.s

  def _Eval(self, node):
    #print('!!', node.tag)

    if node.tag == bool_expr_e.WordTest:
      s = self._EvalCompoundWord(node.w)
      return bool(s)

    if node.tag == bool_expr_e.LogicalNot:
      b = self._Eval(node.child)
      return not b

    if node.tag == bool_expr_e.LogicalAnd:
      # Short-circuit evaluation
      if self._Eval(node.left):
        return self._Eval(node.right)
      else:
        return False

    if node.tag == bool_expr_e.LogicalOr:
      if self._Eval(node.left):
        return True
      else:
        return self._Eval(node.right)

    if node.tag == bool_expr_e.BoolUnary:
      op_id = node.op_id
      s = self._EvalCompoundWord(node.child)

      # Now dispatch on arg type
      arg_type = BOOL_OPS[op_id]
      if arg_type == OperandType.Path:
        try:
          mode = os.stat(s).st_mode
        except OSError as e:  # Python 3: FileNotFoundError
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

    #if node.id == Id.Node_BinaryExpr:
    if node.tag == bool_expr_e.BoolBinary:
      op_id = node.op_id

      s1 = self._EvalCompoundWord(node.left)
      # Whehter to glob escape
      do_fnmatch = op_id in (
          Id.BoolBinary_Equal, Id.BoolBinary_DEqual, Id.BoolBinary_NEqual)
      s2 = self._EvalCompoundWord(node.right, do_fnmatch=do_fnmatch)

      # Now dispatch on arg type
      arg_type = BOOL_OPS[op_id]

      if arg_type == OperandType.Path:
        st1 = os.stat(s1)
        st2 = os.stat(s2)

        if op_id == Id.BoolBinary_nt:
          return True  # TODO: test newer than (mtime)

      if arg_type == OperandType.Int:
        # NOTE: We assume they are constants like [[ 3 -eq 3 ]].
        # Bash also allows [[ 1+2 -eq 3 ]].
        i1 = _StringToInteger(s1)
        i2 = _StringToInteger(s2)

        if op_id == Id.BoolBinary_eq:
          return i1 == i2
        if op_id == Id.BoolBinary_ne:
          return i1 != i2

        raise NotImplementedError(op_id)

      if arg_type == OperandType.Str:
        # TODO:
        # - Compare arrays.  (Although bash coerces them to string first)

        if op_id in (Id.BoolBinary_Equal, Id.BoolBinary_DEqual):
          #log('Comparing %s and %s', s2, s1)
          return libc.fnmatch(s2, s1)

        if op_id == Id.BoolBinary_NEqual:
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
