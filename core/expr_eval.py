#!/usr/bin/env python
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
warn = util.warn
e_die = util.e_die

arith_expr_e = ast.arith_expr_e
lhs_expr_e = ast.lhs_expr_e
bool_expr_e = ast.bool_expr_e  # used for dispatch
word_e = ast.word_e

part_value_e = runtime.part_value_e
value_e = runtime.value_e
lvalue_e = runtime.lvalue_e
scope = runtime.scope


def _StringToInteger(s, word=None):
  """Use bash-like rules to coerce a string to an integer.

  0xAB -- hex constant
  010 -- octable constant
  64#z -- arbitary base constant
  bare word: variable
  quoted word: string

  Dumb stuff like $(( $(echo 1)$(echo 2) + 1 ))  =>  13  is possible.
  """
  # TODO: In non-strict mode, empty string becomes zero.  In strict mode, it's
  # a runtime error.

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


def _ValToArith(val, word=None):
  """Convert runtime.value to Python int or list.

  NOTE: We could have a runtime.arith_value and get rid of the isinstance()
  check.  But this means our array indexing is lazy, which I think is fine.

  PROBLEM: array[1000000]=1 could use up a lot of memory.

  But I think that is OK, at least until there's evidence that people want
  to use arrays that way.

  But what about hash tables?  That should be a separate type.

  Representation could be:

  ['1', 2, 3, None, None, '4', None]
  Then length counts the entries that are not None.
  """
  assert isinstance(val, runtime.value), val
  if val.tag == value_e.Str:
    return _StringToInteger(val.s, word=word)
  if val.tag == value_e.StrArray:
    return val.strs  # Python list of strings


class _ExprEvaluator:
  """
  For now the arith and bool evaluators share some logic.
  """

  def __init__(self, mem, exec_opts, word_ev):
    self.mem = mem
    self.exec_opts = exec_opts
    self.word_ev = word_ev  # type: word_eval.WordEvaluator

  def _StringToIntegerOrError(self, s):
    try:
      i = _StringToInteger(s)
    except util.FatalRuntimeError as e:
      if self.exec_opts.strict_arith:
        raise
      else:
        i = 0
        warn(e.UserErrorString())
    return i

  def _UndefZeroOrError(self):
    if self.exec_opts.strict_arith:
      e_die("Undefined variable")  # TODO: better context
    return 0

  # TODO: Remove this
  def Eval(self, node):
    return self._Eval(node)


class ArithEvaluator(_ExprEvaluator):

  def _ValToArithOrError(self, val, word=None):
    try:
      i = _ValToArith(val, word=word)
    except util.FatalRuntimeError as e:
      if self.exec_opts.strict_arith:
        raise
      else:
        i = 0
        warn(e.UserErrorString())
    return i

  def _VarLookup(self, name):
    val = self.mem.GetVar(name)
    # By default, undefined variables are the ZERO value.  TODO: Respect
    # nounset and raise an exception.
    if val.tag == value_e.Undef:
      if self.exec_opts.nounset:
        # TODO: need token
        e_die('Undefined variable %r', node.name)
      else:
        return 0

    # TODO: It could be an array too!
    return self._ValToArithOrError(val)

  def _EvalLhs(self, node):
    """Evaluate the operand for a++ a[0]++ as an R-value.

    Args:
      node: osh_ast.lhs_expr

    Returns:
      int, runtime.lvalue
    """
    #log('lhs_expr NODE %s', node)
    assert isinstance(node, ast.lhs_expr), node
    if node.tag == lhs_expr_e.LhsName:  # a = b
      # Problem: It can't be an array?  
      # a=(1 2)
      # (( a++ ))
      lval = runtime.LhsName(node.name)
      return self._VarLookup(node.name), lval

    if node.tag == lhs_expr_e.LhsIndexedName:  # a[1] = b
      # See tdop.IsIndexable for valid values:
      # - ArithVarRef (not LhsName): a[1]
      # - FuncCall: f(x), 1
      # - ArithBinary LBracket: f[1][1] -- no semantics for this?

      # TODO: if we get Undef, we should make an empty array, if not
      # 'strict-arith'
      index = self._Eval(node.index)
      lval = runtime.LhsIndexedName(node.name, index)

      val = self.mem.GetVar(node.name)
      if val.tag == value_e.Str:
        e_die("String %r can't be assigned to", node.name)

      if val.tag == value_e.Undef:
        if self.exec_opts.strict_arith:
          # TODO: need token
          e_die('Undefined array %r', node.name)
        # Construct a new array with the index set.
        a = [None] * (index + 1)
        v = 0
        a[index] = v
        return v, lval

      if val.tag == value_e.StrArray:
        #log('ARRAY %s -> %s, index %d', node.name, array, index)
        array = val.strs
        # NOTE: Similar logic in RHS Arith_LBracket
        try:
          v = array[index]
        except IndexError:
          v = self._UndefZeroOrError()
        if isinstance(v, str):
          v = self._StringToIntegerOrError(v)
        return v, lval

    raise AssertionError(node.tag)

  def _Store(self, lval, new_int):
    val = runtime.Str(str(new_int))
    self.mem.SetVar(lval, val, (), scope.Dynamic)

  def _Eval(self, node):
    """
    Args:
      node: osh_ast.arith_expr

    Returns:
      integer
    """
    # OSH semantics: Variable NAMES cannot be formed dynamically; but INTEGERS
    # can.  ${foo:-3}4 is OK.  $? will be a compound word too, so we don't have
    # to handle that as a special case.

    if node.tag == arith_expr_e.ArithVarRef:  # $(( x ))
      return self._VarLookup(node.name)

    # $(( $x )) or $(( ${x}${y} )), etc.
    if node.tag == arith_expr_e.ArithWord:
      val = self.word_ev.EvalWordToString(node.w)
      return self._ValToArithOrError(val, word=node.w)

    if node.tag == arith_expr_e.UnaryAssign:  # a++
      op_id = node.op_id
      old_int, lval = self._EvalLhs(node.child)

      if op_id == Id.Node_PostDPlus:  # post-increment
        new_int = old_int + 1
        ret = old_int

      elif op_id == Id.Node_PostDMinus:  # post-decrement
        new_int = old_int - 1
        ret = old_int

      elif op_id == Id.Arith_DPlus:  # pre-increment
        new_int = old_int + 1
        ret = new_int

      elif op_id == Id.Arith_DMinus:  # pre-decrement
        new_int = old_int - 1
        ret = new_int

      else:
        raise NotImplementedError(op_id)

      #log('old %d new %d ret %d', old_int, new_int, ret)
      self._Store(lval, new_int)
      return ret

    if node.tag == arith_expr_e.BinaryAssign:  # a=1, a+=5, a[1]+=5
      op_id = node.op_id
      old_int, lval = self._EvalLhs(node.left)

      rhs = self._Eval(node.right)

      if op_id == Id.Arith_Equal:
        # NOTE: We don't need old_int for this case.  Evaluating it has no side
        # effects, so it's harmless.
        new_int = rhs
      elif op_id == Id.Arith_PlusEqual:
        new_int = old_int + rhs
      elif op_id == Id.Arith_MinusEqual:
        new_int = old_int - rhs
      elif op_id == Id.Arith_StarEqual:
        new_int = old_int * rhs
      elif op_id == Id.Arith_SlashEqual:
        try:
          new_int = old_int / rhs
        except ZeroDivisionError:
          # TODO: location
          e_die('Divide by zero')
      elif op_id == Id.Arith_PercentEqual:
        new_int = old_int % rhs

      elif op_id == Id.Arith_DGreatEqual:
        new_int = old_int >> rhs
      elif op_id == Id.Arith_DLessEqual:
        new_int = old_int << rhs
      elif op_id == Id.Arith_AmpEqual:
        new_int = old_int & rhs
      elif op_id == Id.Arith_PipeEqual:
        new_int = old_int | rhs
      elif op_id == Id.Arith_CaretEqual:
        new_int = old_int ^ rhs
      else:
        raise AssertionError(op_id)  # shouldn't get here
 
      self._Store(lval, new_int)
      return new_int

    if node.tag == arith_expr_e.ArithUnary:
      op_id = node.op_id

      if op_id == Id.Node_UnaryPlus:
        return self._Eval(node.child)
      if op_id == Id.Node_UnaryMinus:
        return -self._Eval(node.child)

      if op_id == Id.Arith_Bang:  # logical negation
        return int(not self._Eval(node.child))
      if op_id == Id.Arith_Tilde:  # bitwise complement
        return ~self._Eval(node.child)

      raise NotImplementedError(op_id)

    if node.tag == arith_expr_e.ArithBinary:
      op_id = node.op_id

      lhs = self._Eval(node.left)

      # Short-circuit evaluation for || and &&.
      if op_id == Id.Arith_DPipe:
        if lhs == 0:
          rhs = self._Eval(node.right)
          return int(rhs != 0)
        else:
          return 1  # true
      if op_id == Id.Arith_DAmp:
        if lhs == 0:
          return 0  # false
        else:
          rhs = self._Eval(node.right)
          return int(rhs != 0)

      rhs = self._Eval(node.right)  # eager evaluation for the rest

      if op_id == Id.Arith_LBracket:
        if not isinstance(lhs, list):
          # TODO: Add error context
          e_die('Expected array in index expression, got %s', lhs)

        try:
          item = lhs[rhs]
        except IndexError:
          if self.exec_opts.nounset:
            e_die('Index out of bounds')
          else:
            return 0  # If not fatal, return 0

        if isinstance(item, str):
          return self._StringToIntegerOrError(item)
        # We could have an integer if we did 'a=(1 2); (( a[0]=0 ))'
        assert isinstance(item, int), item
        return item

      if op_id == Id.Arith_Comma:
        return rhs

      if op_id == Id.Arith_Plus:
        return lhs + rhs
      if op_id == Id.Arith_Minus:
        return lhs - rhs
      if op_id == Id.Arith_Star:
        return lhs * rhs
      if op_id == Id.Arith_Slash:
        try:
          return lhs / rhs
        except ZeroDivisionError:
          # TODO: Instead of op_id, I should have the token
          # node.right.w crashes if it's not a constant!
          e_die('Divide by zero', word=node.right.w)
      if op_id == Id.Arith_Percent:
        return lhs % rhs
      if op_id == Id.Arith_DStar:
        return lhs ** rhs

      if op_id == Id.Arith_DEqual:
        return int(lhs == rhs)
      if op_id == Id.Arith_NEqual:
        return int(lhs != rhs)
      if op_id == Id.Arith_Great:
        return int(lhs > rhs)
      if op_id == Id.Arith_GreatEqual:
        return int(lhs >= rhs)
      if op_id == Id.Arith_Less:
        return int(lhs < rhs)
      if op_id == Id.Arith_LessEqual:
        return int(lhs <= rhs)

      if op_id == Id.Arith_Pipe:
        return lhs | rhs
      if op_id == Id.Arith_Amp:
        return lhs & rhs
      if op_id == Id.Arith_Caret:
        return lhs ^ rhs

      # Note: how to define shift of negative numbers?
      if op_id == Id.Arith_DLess:
        return lhs << rhs
      if op_id == Id.Arith_DGreat:
        return lhs >> rhs

      raise NotImplementedError(op_id)

    if node.tag == arith_expr_e.TernaryOp:
      cond = self._Eval(node.cond)
      if cond:  # nonzero
        return self._Eval(node.true_expr)
      else:
        return self._Eval(node.false_expr)

    raise NotImplementedError("Unhandled node %r" % node.__class__.__name__)


class BoolEvaluator(_ExprEvaluator):

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
        i1 = self._StringToIntegerOrError(s1)
        i2 = self._StringToIntegerOrError(s2)

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
