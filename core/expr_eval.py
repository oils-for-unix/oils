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
import stat

try:
  import libc  # for fnmatch
except ImportError:
  from benchmarks import fake_libc as libc

from asdl import const
from core import dev
from core import util
from core import state
from core import ui
from core import word
from osh.meta import ast, runtime, types, BOOL_ARG_TYPES, Id

log = util.log
warn = util.warn
e_die = util.e_die

bool_arg_type_e = types.bool_arg_type_e

arith_expr_e = ast.arith_expr_e
lhs_expr_e = ast.lhs_expr_e
bool_expr_e = ast.bool_expr_e  # used for dispatch
word_e = ast.word_e

part_value_e = runtime.part_value_e
value_e = runtime.value_e
lvalue_e = runtime.lvalue_e
scope_e = runtime.scope_e


def _StringToInteger(s, span_id=const.NO_INTEGER):
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
      e_die('Invalid hex constant %r', s, span_id=span_id)
    return integer

  if s.startswith('0'):
    try:
      integer = int(s, 8)
    except ValueError:
      e_die('Invalid octal constant %r', s, span_id=span_id)  # TODO: Show line number
    return integer

  if '#' in s:
    b, digits = s.split('#', 1)
    try:
      base = int(b)
    except ValueError:
      e_die('Invalid base for numeric constant %r',  b, span_id=span_id)

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
        e_die('Invalid digits for numeric constant %r', digits, span_id=span_id)

      if digit >= base:
        e_die('Digits %r out of range for base %d', digits, base, span_id=span_id)

      integer += digit * n
      n *= base
    return integer

  # Plain integer
  try:
    integer = int(s)
  except ValueError:
    e_die("Invalid integer constant %r", s, span_id=span_id)
  return integer


class _ExprEvaluator(object):
  """Shared between arith and bool evaluators.

  They both:

  1. Convert strings to integers, respecting set -o strict_arith.
  2. Look up variables and evaluate words.
  """

  def __init__(self, mem, exec_opts, word_ev, arena):
    self.mem = mem
    self.exec_opts = exec_opts
    self.word_ev = word_ev  # type: word_eval.WordEvaluator
    self.arena = arena

  def _StringToIntegerOrError(self, s, blame_word=None,
                              span_id=const.NO_INTEGER):
    """Used by both [[ $x -gt 3 ]] and (( $x ))."""
    if span_id == const.NO_INTEGER and blame_word:
      span_id = word.LeftMostSpanForWord(blame_word)

    try:
      i = _StringToInteger(s, span_id=span_id)
    except util.FatalRuntimeError as e:
      if self.exec_opts.strict_arith:
        raise
      else:
        i = 0
        # TODO: Need the arena for printing this error?
        #ui.PrettyPrintError(e)
        warn(e.UserErrorString())
    return i


def _LookupVar(name, mem, exec_opts):
  val = mem.GetVar(name)
  # By default, undefined variables are the ZERO value.  TODO: Respect
  # nounset and raise an exception.
  if val.tag == value_e.Undef and exec_opts.nounset:
    e_die('Undefined variable %r', name)  # TODO: need token
  return val


def EvalLhsAndLookup(node, arith_ev, mem, exec_opts):
  """Evaluate the operand for i++, a[0]++, i+=2, a[0]+=2 as an R-value.

  Also used by the Executor for s+='x' and a[42]+='x'.

  Args:
    node: ast.lhs_expr

  Returns:
    runtime.value, runtime.lvalue
  """
  #log('lhs_expr NODE %s', node)
  assert isinstance(node, ast.lhs_expr), node

  if node.tag == lhs_expr_e.LhsName:  # a = b
    # Problem: It can't be an array?
    # a=(1 2)
    # (( a++ ))
    lval = runtime.LhsName(node.name)
    val = _LookupVar(node.name, mem, exec_opts)

  elif node.tag == lhs_expr_e.LhsIndexedName:  # a[1] = b
    # See tdop.IsIndexable for valid values:
    # - ArithVarRef (not LhsName): a[1]
    # - FuncCall: f(x), 1
    # - ArithBinary LBracket: f[1][1] -- no semantics for this?

    index = arith_ev.Eval(node.index)
    lval = runtime.LhsIndexedName(node.name, index)

    val = mem.GetVar(node.name)
    if val.tag == value_e.Str:
      e_die("Can't assign to characters of string %r", node.name)

    elif val.tag == value_e.Undef:
      # It would make more sense for 'nounset' to control this, but bash
      # doesn't work that way.
      #if self.exec_opts.strict_arith:
      #  e_die('Undefined array %r', node.name)
      val = runtime.Str('')

    elif val.tag == value_e.StrArray:

      #log('ARRAY %s -> %s, index %d', node.name, array, index)
      array = val.strs
      # NOTE: Similar logic in RHS Arith_LBracket
      try:
        item = array[index]
      except IndexError:
        item = None

      if item is None:
        val = runtime.Str('')
      else:
        assert isinstance(item, str), item
        val = runtime.Str(item)

    elif val.tag == value_e.AssocArray:  # declare -A a; a['x']+=1
      # TODO: Also need IsAssocArray() check?
      index = arith_ev.Eval(node.index, int_coerce=False)
      lval = runtime.LhsIndexedName(node.name, index)
      raise NotImplementedError

    else:
      raise AssertionError(val.tag)

  else:
    raise AssertionError(node.tag)

  return val, lval


class ArithEvaluator(_ExprEvaluator):

  def _ValToArith(self, val, span_id, int_coerce=True):
    """Convert runtime.value to a Python int or list of strings."""
    assert isinstance(val, runtime.value), '%r %r' % (val, type(val))

    if int_coerce:
      if val.tag == value_e.Undef:  # 'nounset' already handled before got here
        # Happens upon a[undefined]=42, which unfortunately turns into a[0]=42.
        #log('blame_word %s   arena %s', blame_word, self.arena)
        e_die('Coercing undefined value to 0 in arithmetic context',
              span_id=span_id)
        return 0

      if val.tag == value_e.Str:
        # may raise FatalRuntimeError
        return _StringToInteger(val.s, span_id=span_id)

      if val.tag == value_e.StrArray:  # array is valid on RHS, but not on left
        return val.strs

      if val.tag == value_e.AssocArray:
        return val.d

      raise AssertionError(val)

    if val.tag == value_e.Undef:  # 'nounset' already handled before got here
      return ''  # I think nounset is handled elsewhere

    if val.tag == value_e.Str:
      return val.s

    if val.tag == value_e.StrArray:  # array is valid on RHS, but not on left
      return val.strs

    if val.tag == value_e.AssocArray:
      return val.d

  def _ValToArithOrError(self, val, int_coerce=True, blame_word=None,
                         span_id=const.NO_INTEGER):
    if span_id == const.NO_INTEGER and blame_word:
      span_id = word.LeftMostSpanForWord(blame_word)
    #log('_ValToArithOrError span=%s blame=%s', span_id, blame_word)

    try:
      i = self._ValToArith(val, span_id, int_coerce=int_coerce)
    except util.FatalRuntimeError as e:
      if self.exec_opts.strict_arith:
        raise
      else:
        i = 0

        span_id = dev.SpanIdFromError(e)
        if self.arena:  # BoolEvaluator for test builtin doesn't have it.
          if span_id != const.NO_INTEGER:
            ui.PrintFilenameAndLine(span_id, self.arena)
          else:
            log('*** Warning has no location info ***')
        warn(e.UserErrorString())
    return i

  def _LookupVar(self, name):
    return _LookupVar(name, self.mem, self.exec_opts)

  def _EvalLhsAndLookupArith(self, node):
    """
    Args:
      node: lhs_expr
    Returns:
      int or list of strings, runtime.lvalue
    """
    val, lval = EvalLhsAndLookup(node, self, self.mem, self.exec_opts)

    if val.tag == value_e.StrArray:
      e_die("Can't use assignment like ++ or += on arrays")

    # TODO: attribute a span ID here.  There are a few cases, like UnaryAssign
    # and BinaryAssign.
    span_id = word.SpanForLhsExpr(node)
    i = self._ValToArithOrError(val, span_id=span_id)
    return i, lval

  def _EvalLhsArith(self, node):
    """lhs_expr -> lvalue.
    
    Very similar to _EvalLhs in core/cmd_exec."""
    assert isinstance(node, ast.lhs_expr), node

    if node.tag == lhs_expr_e.LhsName:  # (( i = 42 ))
      lval = runtime.LhsName(node.name)
      # TODO: location info.  Use the = token?
      #lval.spids.append(spid)
      return lval

    if node.tag == lhs_expr_e.LhsIndexedName:  # (( a[42] = 42 ))
      # The index of StrArray needs to be coerced to int, but not the index of
      # an AssocArray.
      int_coerce = not self.mem.IsAssocArray(node.name, scope_e.Dynamic)
      index = self.Eval(node.index, int_coerce=int_coerce)

      lval = runtime.LhsIndexedName(node.name, index)
      # TODO: location info.  Use the = token?
      #lval.spids.append(node.spids[0])
      return lval

    raise AssertionError(node.tag)

  def _Store(self, lval, new_int):
    val = runtime.Str(str(new_int))
    self.mem.SetVar(lval, val, (), scope_e.Dynamic)

  def Eval(self, node, int_coerce=True):
    """
    Args:
      node: osh_ast.arith_expr

    Returns:
      int or list of strings
    """
    # OSH semantics: Variable NAMES cannot be formed dynamically; but INTEGERS
    # can.  ${foo:-3}4 is OK.  $? will be a compound word too, so we don't have
    # to handle that as a special case.

    if node.tag == arith_expr_e.ArithVarRef:  # $(( x ))  (can be array)
      tok = node.token
      val = self._LookupVar(tok.val)
      return self._ValToArithOrError(val, int_coerce=int_coerce,
                                     span_id=tok.span_id)

    if node.tag == arith_expr_e.ArithWord:  # $(( $x )) $(( ${x}${y} )), etc.
      val = self.word_ev.EvalWordToString(node.w)
      return self._ValToArithOrError(val, int_coerce=int_coerce, blame_word=node.w)

    if node.tag == arith_expr_e.UnaryAssign:  # a++
      op_id = node.op_id
      old_int, lval = self._EvalLhsAndLookupArith(node.child)

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

      if op_id == Id.Arith_Equal:
        rhs = self.Eval(node.right)
        lval = self._EvalLhsArith(node.left)
        self._Store(lval, rhs)
        return rhs

      old_int, lval = self._EvalLhsAndLookupArith(node.left)
      rhs = self.Eval(node.right)

      if op_id == Id.Arith_PlusEqual:
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
        return self.Eval(node.child)
      if op_id == Id.Node_UnaryMinus:
        return -self.Eval(node.child)

      if op_id == Id.Arith_Bang:  # logical negation
        return int(not self.Eval(node.child))
      if op_id == Id.Arith_Tilde:  # bitwise complement
        return ~self.Eval(node.child)

      raise NotImplementedError(op_id)

    if node.tag == arith_expr_e.ArithBinary:
      op_id = node.op_id

      lhs = self.Eval(node.left)

      # Short-circuit evaluation for || and &&.
      if op_id == Id.Arith_DPipe:
        if lhs == 0:
          rhs = self.Eval(node.right)
          return int(rhs != 0)
        else:
          return 1  # true
      if op_id == Id.Arith_DAmp:
        if lhs == 0:
          return 0  # false
        else:
          rhs = self.Eval(node.right)
          return int(rhs != 0)

      rhs = self.Eval(node.right)  # eager evaluation for the rest

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

        assert isinstance(item, str), item
        return self._StringToIntegerOrError(item)

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
          # TODO: _ErrorWithLocation should also accept arith_expr ?  I
          # think I needed that for other stuff.
          # Or I could blame the '/' token, instead of op_id.
          error_expr = node.right  # node is ArithBinary
          if error_expr.tag == arith_expr_e.ArithVarRef:
            # TODO: ArithVarRef should store a token instead of a string!
            e_die('Divide by zero (name)')
          elif error_expr.tag == arith_expr_e.ArithWord:
            e_die('Divide by zero', word=node.right.w)
          else:
            e_die('Divide by zero')
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
      cond = self.Eval(node.cond)
      if cond:  # nonzero
        return self.Eval(node.true_expr)
      else:
        return self.Eval(node.false_expr)

    raise NotImplementedError("Unhandled node %r" % node.__class__.__name__)


class BoolEvaluator(_ExprEvaluator):

  def _SetRegexMatches(self, matches):
    """For ~= to set the BASH_REMATCH array."""
    state.SetGlobalArray(self.mem, 'BASH_REMATCH', matches)

  def _EvalCompoundWord(self, word, do_fnmatch=False, do_ere=False):
    """
    Args:
      node: Id.Word_Compound
    """
    val = self.word_ev.EvalWordToString(word, do_fnmatch=do_fnmatch,
                                        do_ere=do_ere)
    return val.s

  def Eval(self, node):
    #print('!!', node.tag)

    if node.tag == bool_expr_e.WordTest:
      s = self._EvalCompoundWord(node.w)
      return bool(s)

    if node.tag == bool_expr_e.LogicalNot:
      b = self.Eval(node.child)
      return not b

    if node.tag == bool_expr_e.LogicalAnd:
      # Short-circuit evaluation
      if self.Eval(node.left):
        return self.Eval(node.right)
      else:
        return False

    if node.tag == bool_expr_e.LogicalOr:
      if self.Eval(node.left):
        return True
      else:
        return self.Eval(node.right)

    if node.tag == bool_expr_e.BoolUnary:
      op_id = node.op_id
      s = self._EvalCompoundWord(node.child)

      # Now dispatch on arg type
      arg_type = BOOL_ARG_TYPES[op_id]  # could be static in the LST?

      if arg_type == bool_arg_type_e.Path:
        # Only use lstat if we're testing for a symlink.
        if op_id in (Id.BoolUnary_h, Id.BoolUnary_L):
          try:
            mode = os.lstat(s).st_mode
          except OSError:
            return False

          return stat.S_ISLNK(mode)

        try:
          mode = os.stat(s).st_mode
        except OSError:
          # TODO: Signal extra debug information?
          #log("Error from stat(%r): %s" % (s, e))
          return False

        if op_id in (Id.BoolUnary_e, Id.BoolUnary_a):  # -a is alias for -e
          return True

        if op_id == Id.BoolUnary_f:
          return stat.S_ISREG(mode)

        if op_id == Id.BoolUnary_d:
          return stat.S_ISDIR(mode)

        if op_id == Id.BoolUnary_x:
          return os.access(s, os.X_OK)

        if op_id == Id.BoolUnary_r:
          return os.access(s, os.R_OK)

        if op_id == Id.BoolUnary_w:
          return os.access(s, os.W_OK)

        raise NotImplementedError(op_id)

      if arg_type == bool_arg_type_e.Str:
        if op_id == Id.BoolUnary_z:
          return not bool(s)
        if op_id == Id.BoolUnary_n:
          return bool(s)

        raise NotImplementedError(op_id)

      if arg_type == bool_arg_type_e.Other:
        if op_id == Id.BoolUnary_t:
          try:
            fd = int(s)
          except ValueError:
            # TODO: Need location information of [
            e_die('Invalid file descriptor %r', s)
          return os.isatty(fd)

        raise NotImplementedError(op_id)

      raise NotImplementedError(arg_type)

    if node.tag == bool_expr_e.BoolBinary:
      op_id = node.op_id

      s1 = self._EvalCompoundWord(node.left)
      # Whether to glob escape
      do_fnmatch = op_id in (Id.BoolBinary_GlobEqual, Id.BoolBinary_GlobDEqual,
                             Id.BoolBinary_GlobNEqual)
      do_ere = (op_id == Id.BoolBinary_EqualTilde)
      s2 = self._EvalCompoundWord(node.right, do_fnmatch=do_fnmatch,
                                  do_ere=do_ere)

      # Now dispatch on arg type
      arg_type = BOOL_ARG_TYPES[op_id]

      if arg_type == bool_arg_type_e.Path:
        st1 = os.stat(s1)
        st2 = os.stat(s2)

        # TODO: test newer than (mtime)
        if op_id == Id.BoolBinary_nt:
          return st1[stat.ST_MTIME] > st2[stat.ST_MTIME]
        if op_id == Id.BoolBinary_ot:
          return st1[stat.ST_MTIME] < st2[stat.ST_MTIME]

        raise NotImplementedError(op_id)

      if arg_type == bool_arg_type_e.Int:
        # NOTE: We assume they are constants like [[ 3 -eq 3 ]].
        # Bash also allows [[ 1+2 -eq 3 ]].
        i1 = self._StringToIntegerOrError(s1, blame_word=node.left)
        i2 = self._StringToIntegerOrError(s2, blame_word=node.right)

        if op_id == Id.BoolBinary_eq:
          return i1 == i2
        if op_id == Id.BoolBinary_ne:
          return i1 != i2
        if op_id == Id.BoolBinary_gt:
          return i1 > i2
        if op_id == Id.BoolBinary_ge:
          return i1 >= i2
        if op_id == Id.BoolBinary_lt:
          return i1 < i2
        if op_id == Id.BoolBinary_le:
          return i1 <= i2

        raise NotImplementedError(op_id)

      if arg_type == bool_arg_type_e.Str:

        if op_id in (Id.BoolBinary_GlobEqual, Id.BoolBinary_GlobDEqual):
          #log('Matching %s against pattern %s', s1, s2)

          # TODO: Respect extended glob?  * and ! and ? are quoted improperly.
          # But @ and + are OK.
          return libc.fnmatch(s2, s1)

        if op_id == Id.BoolBinary_GlobNEqual:
          return not libc.fnmatch(s2, s1)

        if op_id in (Id.BoolBinary_Equal, Id.BoolBinary_DEqual):
          return s1 == s2

        if op_id == Id.BoolBinary_NEqual:
          return s1 != s2

        if op_id == Id.BoolBinary_EqualTilde:
          #log('Matching %r against regex %r', s1, s2)
          try:
            matches = libc.regex_match(s2, s1)
          except RuntimeError:
            # 2 means a parse error.  Note this is a fatal error in OSH but not
            # in bash.
            e_die("Invalid regex %r", s2, word=node.right, status=2)

          if matches is None:
            return False

          self._SetRegexMatches(matches)
          return True

        if op_id == Id.Redir_Less:  # pun
          return s1 < s2

        if op_id == Id.Redir_Great:  # pun
          return s1 > s2

        raise NotImplementedError(op_id)

    raise AssertionError(node.tag)
