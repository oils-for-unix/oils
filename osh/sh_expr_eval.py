#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
expr_eval.py -- Currently used for boolean and arithmetic expressions.
"""

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import (
    scope_e, scope_t,
    quote_e, quote_t,
    lvalue, lvalue_t, 
    value, value_e, value_t, value__Str, value__Int, value__MaybeStrArray,
    value__AssocArray, value__Obj,
)
from _devbuild.gen.syntax_asdl import (
    arith_expr_e, arith_expr_t, arith_expr__VarRef, arith_expr__ArithWord,
    arith_expr__Unary, arith_expr__Binary, arith_expr__UnaryAssign,
    arith_expr__BinaryAssign, arith_expr__TernaryOp,
    bool_expr_e, bool_expr_t, bool_expr__WordTest, bool_expr__LogicalNot,
    bool_expr__LogicalAnd, bool_expr__LogicalOr, bool_expr__Unary,
    bool_expr__Binary,
    sh_lhs_expr_e, sh_lhs_expr_t, sh_lhs_expr__Name, sh_lhs_expr__IndexedName,
    word_t,
)
from _devbuild.gen.types_asdl import bool_arg_type_e
from asdl import runtime
from core import error
from core import state
from core import ui
from core.util import e_die, log
from frontend import location
from frontend import consts
from frontend import match
from mycpp import mylib
from mycpp.mylib import tagswitch, switch
from osh import bool_stat
from osh import word_

import libc  # for fnmatch

from typing import List, Tuple, Optional, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from core.ui import ErrorFormatter
  from core import optview
  from core.state import Mem
  from osh import word_eval

_ = log


def _StringToInteger(s, span_id=runtime.NO_SPID):
  # type: (str, int) -> int
  """Use bash-like rules to coerce a string to an integer.

  Runtime parsing enables silly stuff like $(( $(echo 1)$(echo 2) + 1 )) => 13

  0xAB -- hex constant
  042  -- octal constant
  42   -- decimal constant
  64#z -- arbitary base constant

  bare word: variable
  quoted word: string (not done?)
  """
  if s.startswith('0x'):
    try:
      integer = int(s, 16)
    except ValueError:
      e_die('Invalid hex constant %r', s, span_id=span_id)
    return integer

  if s.startswith('0'):
    try:
      integer = int(s, 8)
    except ValueError:
      e_die('Invalid octal constant %r', s, span_id=span_id)
    return integer

  if '#' in s:
    parts = s.split('#', 1)  # mycpp rewrite: can't use dynamic unpacking of List
    b = parts[0]
    digits = parts[1]
    try:
      base = int(b)
    except ValueError:
      e_die('Invalid base for numeric constant %r',  b, span_id=span_id)

    integer = 0
    n = 1
    for ch in digits:
      if 'a' <= ch and ch <= 'z':
        digit = ord(ch) - ord('a') + 10
      elif 'A' <= ch and ch <= 'Z':
        digit = ord(ch) - ord('A') + 36
      elif ch == '@':  # horrible syntax
        digit = 62
      elif ch == '_':
        digit = 63
      elif ch.isdigit():
        digit = int(ch)
      else:
        e_die('Invalid digits for numeric constant %r', digits, span_id=span_id)

      if digit >= base:
        e_die('Digits %r out of range for base %d', digits, base, span_id=span_id)

      integer += digit * n
      n *= base
    return integer

  # Normal base 10 integer
  try:
    integer = int(s)
  except ValueError:
    e_die("Invalid integer constant %r", s, span_id=span_id)
  return integer


#
# Common logic for Arith and Command/Word variants of the same expression
#
# Calls EvalLhs()
#   a[$key]=$val             # osh/cmd_exec.py:814  (command_e.ShAssignment)
# Calls _EvalLhsArith()
#   (( a[key] = val ))       # osh/sh_expr_eval.py:326 (_EvalLhsArith)
#
# Calls EvalLhsAndLookup():
#   a[$key]+=$val            # osh/cmd_exec.py:795     (assign_op_e.PlusEqual)
#   (( a[key] += val ))      # osh/sh_expr_eval.py:308 (_EvalLhsAndLookupArith)
#
# Uses Python's [] operator
#   val=${a[$key]}           # osh/word_eval.py:639 (bracket_op_e.ArrayIndex)
#   (( val = a[key] ))       # osh/sh_expr_eval.py:509 (Id.Arith_LBracket)
#


def _LookupVar(name, mem, exec_opts):
  # type: (str, Mem, optview.Exec) -> value_t
  val = mem.GetVar(name)
  # By default, undefined variables are the ZERO value.  TODO: Respect
  # nounset and raise an exception.
  if val.tag_() == value_e.Undef and exec_opts.nounset():
    e_die('Undefined variable %r', name)  # TODO: need token
  return val


def EvalLhs(node, arith_ev, mem, spid, lookup_mode):
  # type: (sh_lhs_expr_t, ArithEvaluator, Mem, int, scope_t) -> lvalue_t
  """Evaluate a shell "place" expression.

  Used for a=b and a[x]=b
  """
  assert isinstance(node, sh_lhs_expr_t), node

  UP_node = node
  lval = None  # type: lvalue_t
  with tagswitch(node) as case:
    if case(sh_lhs_expr_e.Name):  # a=x
      node = cast(sh_lhs_expr__Name, UP_node)

      # Note: C++ constructor doesn't take spids directly.  Should we add that?
      lval1 = lvalue.Named(node.name)
      lval1.spids.append(spid)
      lval = lval1

    elif case(sh_lhs_expr_e.IndexedName):  # a[1+2]=x
      node = cast(sh_lhs_expr__IndexedName, UP_node)

      if mem.IsAssocArray(node.name, lookup_mode):
        key = arith_ev.EvalWordToString(node.index)
        # copy left-mode spid
        lval2 = lvalue.Keyed(node.name, key)
        lval2.spids.append(node.spids[0])
        lval = lval2
      else:
        index = arith_ev.EvalToInt(node.index)
        # copy left-mode spid
        lval3 = lvalue.Indexed(node.name, index)
        lval3.spids.append(node.spids[0])
        lval = lval3

    else:
      raise AssertionError(node.tag_())

  return lval


def _EvalLhsArith(node, mem, arith_ev):
  # type: (sh_lhs_expr_t, Mem, ArithEvaluator) -> lvalue_t
  """Evaluate an arithmetic "place" expression.
  
  Very similar to EvalLhs above, called in osh/cmd_exec.py.
  """
  assert isinstance(node, sh_lhs_expr_t), node

  UP_node = node
  with tagswitch(node) as case:
    if case(sh_lhs_expr_e.Name):  # (( i = 42 ))
      node = cast(sh_lhs_expr__Name, UP_node)

      lval = lvalue.Named(node.name)  # type: lvalue_t
      # TODO: location info.  Use the = token?
      #lval.spids.append(spid)

    elif case(sh_lhs_expr_e.IndexedName):  # (( a[42] = 42 ))
      node = cast(sh_lhs_expr__IndexedName, UP_node)

      # The index of MaybeStrArray needs to be coerced to int, but not the
      # index of an AssocArray.
      if mem.IsAssocArray(node.name, scope_e.Dynamic):
        key = arith_ev.EvalWordToString(node.index)
        lval = lvalue.Keyed(node.name, key)
      else:
        index = arith_ev.EvalToInt(node.index)
        lval = lvalue.Indexed(node.name, index)
        # TODO: location info.  Use the = token?
        #lval.spids.append(node.spids[0])

    else:
      raise AssertionError(node.tag_())

  return lval


def EvalLhsAndLookup(node, arith_ev, mem, exec_opts,
                     lookup_mode=scope_e.Dynamic):
  # type: (sh_lhs_expr_t, ArithEvaluator, Mem, optview.Exec, scope_t) -> Tuple[value_t, lvalue_t]
  """Evaluate the operand for i++, a[0]++, i+=2, a[0]+=2 as an R-value.

  Also used by the Executor for s+='x' and a[42]+='x'.

  Args:
    node: syntax_asdl.sh_lhs_expr

  Returns:
    value_t, lvalue_t
  """
  #log('sh_lhs_expr NODE %s', node)

  assert isinstance(node, sh_lhs_expr_t), node

  UP_node = node
  with tagswitch(node) as case:
    if case(sh_lhs_expr_e.Name):  # a = b
      node = cast(sh_lhs_expr__Name, UP_node)
      # Problem: It can't be an array?
      # a=(1 2)
      # (( a++ ))
      lval = lvalue.Named(node.name)  # type: lvalue_t
      val = _LookupVar(node.name, mem, exec_opts)

    elif case(sh_lhs_expr_e.IndexedName):  # a[1] = b
      node = cast(sh_lhs_expr__IndexedName, UP_node)
      # See tdop.IsIndexable for valid values:
      # - VarRef (not Name): a[1]
      # - FuncCall: f(x), 1
      # - Binary LBracket: f[1][1] -- no semantics for this?

      val = mem.GetVar(node.name)

      UP_val = val
      with tagswitch(val) as case2:
        if case2(value_e.Str):
          e_die("Can't assign to characters of string %r", node.name)

        elif case2(value_e.Undef):
          # compatible behavior: Treat it like an array.
          # TODO: Does this code ever get triggered?  It seems like the error is
          # caught earlier.

          index = arith_ev.EvalToInt(node.index)
          lval = lvalue.Indexed(node.name, index)
          if exec_opts.nounset():
            e_die("Undefined variable can't be indexed")
          else:
            val = value.Str('')

        elif case2(value_e.MaybeStrArray):
          array_val = cast(value__MaybeStrArray, UP_val)

          #log('ARRAY %s -> %s, index %d', node.name, array, index)
          index = arith_ev.EvalToInt(node.index)
          lval = lvalue.Indexed(node.name, index)
          # NOTE: Similar logic in RHS Arith_LBracket
          try:
            s = array_val.strs[index]
          except IndexError:
            s = None

          if s is None:
            val = value.Str('')  # NOTE: Other logic is value.Undef()?  0?
          else:
            assert isinstance(s, str), s
            val = value.Str(s)

        elif case2(value_e.AssocArray):  # declare -A a; a['x']+=1
          assoc_val = cast(value__AssocArray, UP_val)

          key = arith_ev.EvalWordToString(node.index)
          lval = lvalue.Keyed(node.name, key)

          s = assoc_val.d.get(key)
          if s is None:
            val = value.Str('')
          else:
            val = value.Str(s)

        else:
          raise AssertionError(val.tag_())

    else:
      raise AssertionError(node.tag_())

  return val, lval


class _ExprEvaluator(object):
  """Shared between arith and bool evaluators.

  They both:

  1. Convert strings to integers, respecting shopt -s strict_arith.
  2. Look up variables and evaluate words.
  """

  def __init__(self, mem, exec_opts, errfmt):
    # type: (Mem, optview.Exec, ErrorFormatter) -> None
    self.word_ev = None  # type: word_eval.StringWordEvaluator
    self.mem = mem
    self.exec_opts = exec_opts
    self.errfmt = errfmt

  def CheckCircularDeps(self):
    # type: () -> None
    assert self.word_ev is not None


class ArithEvaluator(_ExprEvaluator):

  def __init__(self, mem, exec_opts, errfmt):
    # type: (Mem, optview.Exec, ErrorFormatter) -> None
    """Redundant constructor for mycpp."""
    _ExprEvaluator.__init__(self, mem, exec_opts, errfmt)

  def _ValToIntOrError(self, val, span_id=runtime.NO_SPID):
    # type: (value_t, int) -> int
    try:
      UP_val = val
      with tagswitch(val) as case:
        if case(value_e.Undef):  # 'nounset' already handled before got here
          # Happens upon a[undefined]=42, which unfortunately turns into a[0]=42.
          #log('blame_word %s   arena %s', blame_word, self.arena)
          e_die('Undefined value in arithmetic context', span_id=span_id)

        elif case(value_e.Int):
          val = cast(value__Int, UP_val)
          return val.i

        elif case(value_e.Str):
          val = cast(value__Str, UP_val)
          return _StringToInteger(val.s, span_id=span_id)  # calls e_die

        elif case(value_e.Obj):
          # Note: this handles var x = 42; echo $(( x > 2 )).
          if mylib.PYTHON:
            val = cast(value__Obj, UP_val)
            if isinstance(val.obj, int):
              return val.obj
          raise AssertionError()  # not in C++

    except error.FatalRuntime as e:
      if self.exec_opts.strict_arith():
        raise
      else:
        span_id = word_.SpanIdFromError(e)
        self.errfmt.PrettyPrintError(e, prefix='warning: ')
        return 0

    # Arrays and associative arrays always fail -- not controlled by strict_arith.
    # In bash, (( a )) is like (( a[0] )), but I don't want that.
    # And returning '0' gives different results.
    e_die("Expected a value convertible to integer, got %s",
          ui.ValType(val), span_id=span_id)

  def _EvalLhsAndLookupArith(self, node):
    # type: (sh_lhs_expr_t) -> Tuple[int, lvalue_t]
    """
    Args:
      node: sh_lhs_expr

    Returns:
      (Python object, lvalue_t)
    """
    val, lval = EvalLhsAndLookup(node, self, self.mem, self.exec_opts)

    if val.tag_() == value_e.MaybeStrArray:
      e_die("Can't use assignment like ++ or += on arrays")

    # TODO: attribute a span ID here.  There are a few cases, like UnaryAssign
    # and BinaryAssign.
    span_id = word_.SpanForLhsExpr(node)
    i = self._ValToIntOrError(val, span_id=span_id)
    return i, lval

  def _Store(self, lval, new_int):
    # type: (lvalue_t, int) -> None
    val = value.Str(str(new_int))
    self.mem.SetVar(lval, val, scope_e.Dynamic)

  def EvalToInt(self, node):
    # type: (arith_expr_t) -> int
    """Used externally by ${a[i+1]} and ${a:start:len}.

    Also used internally.
    """
    val = self.Eval(node)
    # TODO: Can we avoid the runtime cost of adding location info?
    span_id = location.SpanForArithExpr(node)
    i = self._ValToIntOrError(val, span_id=span_id)
    return i

  def Eval(self, node):
    # type: (arith_expr_t) -> value_t
    """
    Args:
      node: arith_expr_t

    Returns:
      None for Undef  (e.g. empty cell)  TODO: Don't return 0!
      int for Str
      List[int] for MaybeStrArray
      Dict[str, str] for AssocArray (TODO: Should we support this?)

    NOTE: (( A['x'] = 'x' )) and (( x = A['x'] )) are syntactically valid in
    bash, but don't do what you'd think.  'x' sometimes a variable name and
    sometimes a key.
    """
    # OSH semantics: Variable NAMES cannot be formed dynamically; but INTEGERS
    # can.  ${foo:-3}4 is OK.  $? will be a compound word too, so we don't have
    # to handle that as a special case.

    UP_node = node
    with tagswitch(node) as case:
      if case(arith_expr_e.VarRef):  # $(( x ))  (can be array)
        node = cast(arith_expr__VarRef, UP_node)
        tok = node.token
        return _LookupVar(tok.val, self.mem, self.exec_opts)

      elif case(arith_expr_e.ArithWord):  # $(( $x )) $(( ${x}${y} )), etc.
        node = cast(arith_expr__ArithWord, UP_node)
        return self.word_ev.EvalWordToString(node.w)

      elif case(arith_expr_e.UnaryAssign):  # a++
        node = cast(arith_expr__UnaryAssign, UP_node)

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
          raise AssertionError(op_id)

        #log('old %d new %d ret %d', old_int, new_int, ret)
        self._Store(lval, new_int)
        return value.Int(ret)

      elif case(arith_expr_e.BinaryAssign):  # a=1, a+=5, a[1]+=5
        node = cast(arith_expr__BinaryAssign, UP_node)
        op_id = node.op_id

        if op_id == Id.Arith_Equal:
          lval = _EvalLhsArith(node.left, self.mem, self)
          # Disallowing (( a = myarray ))
          # It has to be an integer
          rhs_int = self.EvalToInt(node.right)
          self._Store(lval, rhs_int)
          return value.Int(rhs_int)

        old_int, lval = self._EvalLhsAndLookupArith(node.left)
        rhs = self.EvalToInt(node.right)

        if op_id == Id.Arith_PlusEqual:
          new_int = old_int + rhs
        elif op_id == Id.Arith_MinusEqual:
          new_int = old_int - rhs
        elif op_id == Id.Arith_StarEqual:
          new_int = old_int * rhs

        elif op_id == Id.Arith_SlashEqual:
          if rhs == 0:
            e_die('Divide by zero')  # TODO: location
          new_int = old_int / rhs

        elif op_id == Id.Arith_PercentEqual:
          if rhs == 0:
            e_die('Divide by zero')  # TODO: location
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
        return value.Int(new_int)

      elif case(arith_expr_e.Unary):
        node = cast(arith_expr__Unary, UP_node)
        op_id = node.op_id

        i = self.EvalToInt(node.child)

        if op_id == Id.Node_UnaryPlus:
          ret = i
        elif op_id == Id.Node_UnaryMinus:
          ret = -i

        elif op_id == Id.Arith_Bang:  # logical negation
          ret = 1 if i == 0 else 0
        elif op_id == Id.Arith_Tilde:  # bitwise complement
          ret = ~i
        else:
          raise AssertionError(op_id)  # shouldn't get here

        return value.Int(ret)

      elif case(arith_expr_e.Binary):
        node = cast(arith_expr__Binary, UP_node)
        op_id = node.op_id

        # Short-circuit evaluation for || and &&.
        if op_id == Id.Arith_DPipe:
          lhs = self.EvalToInt(node.left)
          if lhs == 0:
            rhs = self.EvalToInt(node.right)
            ret = int(rhs != 0)
          else:
            ret = 1  # true
          return value.Int(ret)

        if op_id == Id.Arith_DAmp:
          lhs = self.EvalToInt(node.left)
          if lhs == 0:
            ret = 0  # false
          else:
            rhs = self.EvalToInt(node.right)
            ret = int(rhs != 0)
          return value.Int(ret)

        if op_id == Id.Arith_LBracket:
          # NOTE: Similar to bracket_op_e.ArrayIndex in osh/word_eval.py

          left = self.Eval(node.left)
          UP_left = left
          with tagswitch(left) as case:
            if case(value_e.MaybeStrArray):
              left = cast(value__MaybeStrArray, UP_left)
              rhs_int = self.EvalToInt(node.right)
              try:
                # could be None because representation is sparse
                s = left.strs[rhs_int]
              except IndexError:
                s = None

            elif case(value_e.AssocArray):
              left = cast(value__AssocArray, UP_left)
              key = self.EvalWordToString(node.right)
              s = left.d.get(key)

            else:
              # TODO: Add error context
              e_die('Expected array or assoc in index expression, got %s',
                    ui.ValType(left))

          if s is None:
            val = value.Undef()  # type: value_t
          else:
            val = value.Str(s)

          return val

        if op_id == Id.Arith_Comma:
          self.Eval(node.left)  # throw away result
          return self.Eval(node.right)

        # Rest are integers
        lhs = self.EvalToInt(node.left)
        rhs = self.EvalToInt(node.right)

        if op_id == Id.Arith_Plus:
          ret = lhs + rhs
        elif op_id == Id.Arith_Minus:
          ret = lhs - rhs
        elif op_id == Id.Arith_Star:
          ret =  lhs * rhs
        elif op_id == Id.Arith_Slash:
          if rhs == 0:
            # TODO: Could also blame /
            e_die('Divide by zero',
                  span_id=location.SpanForArithExpr(node.right))

          ret = lhs / rhs

        elif op_id == Id.Arith_Percent:
          if rhs == 0:
            # TODO: Could also blame /
            e_die('Divide by zero',
                  span_id=location.SpanForArithExpr(node.right))

          ret = lhs % rhs

        elif op_id == Id.Arith_DStar:
          # OVM is stripped of certain functions that are somehow necessary for
          # exponentiation.
          # Python/ovm_stub_pystrtod.c:21: PyOS_double_to_string: Assertion `0'
          # failed.
          if rhs < 0:
            e_die("Exponent can't be less than zero")  # TODO: error location
          ret = 1
          for i in xrange(rhs):
            ret *= lhs

        elif op_id == Id.Arith_DEqual:
          ret = int(lhs == rhs)
        elif op_id == Id.Arith_NEqual:
          ret = int(lhs != rhs)
        elif op_id == Id.Arith_Great:
          ret = int(lhs > rhs)
        elif op_id == Id.Arith_GreatEqual:
          ret = int(lhs >= rhs)
        elif op_id == Id.Arith_Less:
          ret = int(lhs < rhs)
        elif op_id == Id.Arith_LessEqual:
          ret = int(lhs <= rhs)

        elif op_id == Id.Arith_Pipe:
          ret = lhs | rhs
        elif op_id == Id.Arith_Amp:
          ret = lhs & rhs
        elif op_id == Id.Arith_Caret:
          ret = lhs ^ rhs

        # Note: how to define shift of negative numbers?
        elif op_id == Id.Arith_DLess:
          ret = lhs << rhs
        elif op_id == Id.Arith_DGreat:
          ret = lhs >> rhs
        else:
          raise AssertionError(op_id)

        return value.Int(ret)

      elif case(arith_expr_e.TernaryOp):
        node = cast(arith_expr__TernaryOp, UP_node)

        cond = self.EvalToInt(node.cond)
        if cond:  # nonzero
          return self.Eval(node.true_expr)
        else:
          return self.Eval(node.false_expr)

      else:
        raise AssertionError(node.tag_())

  def EvalWordToString(self, node):
    # type: (arith_expr_t) -> str
    """
    Args:
      node: arith_expr_t

    Returns:
      str

    Raises:
      error.FatalRuntime if the expression isn't a string
      Or if it contains a bare variable like a[x]

    These are allowed because they're unambiguous, unlike a[x]

    a[$x] a["$x"] a["x"] a['x']
    """
    UP_node = node
    if node.tag_() == arith_expr_e.ArithWord:  # $(( $x )) $(( ${x}${y} )), etc.
      node = cast(arith_expr__ArithWord, UP_node)
      val = self.word_ev.EvalWordToString(node.w)
      return val.s
    else:
      # TODO: location info for orginal
      e_die("Associative array keys must be strings: $x 'x' \"$x\" etc.")


class BoolEvaluator(_ExprEvaluator):

  def __init__(self, mem, exec_opts, errfmt):
    # type: (Mem, optview.Exec, ErrorFormatter) -> None
    _ExprEvaluator.__init__(self, mem, exec_opts, errfmt)
    self.always_strict = False

  def Init_AlwaysStrict(self):
    # type: () -> None
    """For builtin_bracket.py."""
    self.always_strict = True

  def _StringToIntegerOrError(self, s, blame_word=None):
    # type: (str, Optional[word_t]) -> int
    """Used by both [[ $x -gt 3 ]] and (( $x ))."""
    if blame_word:
      span_id = word_.LeftMostSpanForWord(blame_word)
    else:
      span_id = runtime.NO_SPID

    try:
      i = _StringToInteger(s, span_id=span_id)
    except error.FatalRuntime as e:
      if self.always_strict or self.exec_opts.strict_arith():
        raise
      else:
        self.errfmt.PrettyPrintError(e, prefix='warning: ')
        i = 0
    return i

  def _EvalCompoundWord(self, word, quote_kind=quote_e.Default):
    # type: (word_t, quote_t) -> str
    val = self.word_ev.EvalWordToString(word, quote_kind=quote_kind)
    return val.s

  def _SetRegexMatches(self, matches):
    # type: (List[str]) -> None
    """For ~= to set the BASH_REMATCH array."""
    state.SetGlobalArray(self.mem, 'BASH_REMATCH', matches)

  def Eval(self, node):
    # type: (bool_expr_t) -> bool

    UP_node = node
    with tagswitch(node) as case:
      if case(bool_expr_e.WordTest):
        node = cast(bool_expr__WordTest, UP_node)
        s = self._EvalCompoundWord(node.w)
        return bool(s)

      elif case(bool_expr_e.LogicalNot):
        node = cast(bool_expr__LogicalNot, UP_node)
        b = self.Eval(node.child)
        return not b

      elif case(bool_expr_e.LogicalAnd):
        node = cast(bool_expr__LogicalAnd, UP_node)
        # Short-circuit evaluation
        if self.Eval(node.left):
          return self.Eval(node.right)
        else:
          return False

      elif case(bool_expr_e.LogicalOr):
        node = cast(bool_expr__LogicalOr, UP_node)
        if self.Eval(node.left):
          return True
        else:
          return self.Eval(node.right)

      elif case(bool_expr_e.Unary):
        node = cast(bool_expr__Unary, UP_node)
        op_id = node.op_id
        s = self._EvalCompoundWord(node.child)

        # Now dispatch on arg type
        arg_type = consts.BoolArgType(op_id)  # could be static in the LST?

        if arg_type == bool_arg_type_e.Path:
          return bool_stat.DoUnaryOp(op_id, s)

        if arg_type == bool_arg_type_e.Str:
          if op_id == Id.BoolUnary_z:
            return not bool(s)
          if op_id == Id.BoolUnary_n:
            return bool(s)

          raise AssertionError(op_id)  # should never happen

        if arg_type == bool_arg_type_e.Other:
          if op_id == Id.BoolUnary_t:
            try:
              fd = int(s)
            except ValueError:
              # TODO: Need location information of [
              e_die('Invalid file descriptor %r', s, word=node.child)
            return bool_stat.isatty(fd, s, node.child)

          # See whether 'set -o' options have been set
          if op_id == Id.BoolUnary_o:
            index = match.MatchOption(s)
            if index == 0:
              return False
            else:
              return self.exec_opts.opt_array[index]

          if op_id == Id.BoolUnary_v:
            val = self.mem.GetVar(s)
            return val.tag_() != value_e.Undef

          e_die("%s isn't implemented", ui.PrettyId(op_id))  # implicit location

        raise AssertionError(arg_type)  # should never happen

      elif case(bool_expr_e.Binary):
        node = cast(bool_expr__Binary, UP_node)

        op_id = node.op_id
        # Whether to glob escape
        with switch(op_id) as case2:
          if case2(Id.BoolBinary_GlobEqual, Id.BoolBinary_GlobDEqual,
                   Id.BoolBinary_GlobNEqual):
            quote_kind = quote_e.FnMatch
          elif case2(Id.BoolBinary_EqualTilde):
            quote_kind = quote_e.ERE
          else:
            quote_kind = quote_e.Default

        s1 = self._EvalCompoundWord(node.left)
        s2 = self._EvalCompoundWord(node.right, quote_kind=quote_kind)

        # Now dispatch on arg type
        arg_type = consts.BoolArgType(op_id)

        if arg_type == bool_arg_type_e.Path:
          return bool_stat.DoBinaryOp(op_id, s1, s2)

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

          raise AssertionError(op_id)  # should never happen

        if arg_type == bool_arg_type_e.Str:

          if op_id in (Id.BoolBinary_GlobEqual, Id.BoolBinary_GlobDEqual):
            #log('Matching %s against pattern %s', s1, s2)
            return libc.fnmatch(s2, s1)

          if op_id == Id.BoolBinary_GlobNEqual:
            return not libc.fnmatch(s2, s1)

          if op_id in (Id.BoolBinary_Equal, Id.BoolBinary_DEqual):
            return s1 == s2

          if op_id == Id.BoolBinary_NEqual:
            return s1 != s2

          if op_id == Id.BoolBinary_EqualTilde:
            # TODO: This should go to --debug-file
            #log('Matching %r against regex %r', s1, s2)
            try:
              matches = libc.regex_match(s2, s1)
            except RuntimeError:
              # Status 2 indicates a regex parse error.  This is fatal in OSH but
              # not in bash, which treats [[ like a command with an exit code.
              e_die("Invalid regex %r", s2, word=node.right, status=2)

            if matches is None:
              return False

            self._SetRegexMatches(matches)
            return True

          if op_id == Id.Op_Less:
            return s1 < s2

          if op_id == Id.Op_Great:
            return s1 > s2

          raise AssertionError(op_id)  # should never happen

    raise AssertionError(node.tag_())
