#!/usr/bin/env python2
"""
expr_eval.py
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Id_t, Kind
from _devbuild.gen.syntax_asdl import (
    loc, loc_t, Token, word_part, word_part_t,
    SingleQuoted, DoubleQuoted, BracedVarSub, SimpleVarSub, ShArrayLiteral,
    CommandSub,

    expr, expr_e, expr_t, place_expr, place_expr_e, place_expr_t,
    Attribute, Subscript,
    re, re_e, re_t, 
    class_literal_term, class_literal_term_e, class_literal_term_t,
    char_class_term, char_class_term_t,
    PosixClass, PerlClass, CharCode,
)
from _devbuild.gen.runtime_asdl import (
    scope_e, scope_t,
    part_value, part_value_t,
    lvalue,
    value, value_e, value_t,
)
from asdl import runtime
from core import error
from core.error import e_die, e_die_status
from core import state
from frontend import consts
from frontend import match
from frontend import location
from oil_lang import objects
from osh import braces
from osh import word_compile
from mycpp.mylib import log, NewDict, tagswitch

import libc

from typing import cast, Any, Union, Optional, Dict, List, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import lvalue, lvalue_t
  from _devbuild.gen.syntax_asdl import ArgList
  from core.vm import _Executor
  from core.ui import ErrorFormatter
  from core.state import Mem
  from osh.word_eval import AbstractWordEvaluator
  from osh import split

_ = log


def LookupVar(mem, var_name, which_scopes, var_loc):
  # type: (Mem, str, scope_t, loc_t) -> Any
  """Convert to a Python object so we can calculate on it natively."""

  # Lookup WITHOUT dynamic scope.
  val = mem.GetValue(var_name, which_scopes=which_scopes)
  if val.tag() == value_e.Undef:
    # TODO: Location info
    e_die('Undefined variable %r' % var_name, var_loc)

  UP_val = val
  with tagswitch(val) as case:
    if case(value_e.Str):
      val = cast(value.Str, UP_val)
      return val.s

    elif case(value_e.MaybeStrArray):
      val = cast(value.MaybeStrArray, UP_val)
      return val.strs  # node: has None

    elif case(value_e.AssocArray):
      val = cast(value.AssocArray, UP_val)
      return val.d

    elif case(value_e.Obj):
      val = cast(value.Obj, UP_val)
      return val.obj

    else:
      raise NotImplementedError()


def Stringify(py_val, word_part=None):
  # type: (Any, Optional[word_part_t]) -> str
  """ For predictably converting between Python objects and strings.

  We don't want to tie our sematnics to the Python interpreter too much.
  """
  if isinstance(py_val, bool):
    return 'true' if py_val else 'false'  # Use JSON spelling

  if isinstance(py_val, objects.Regex):  # TODO: This should be a variant of value_t?
    return py_val.AsPosixEre()

  if not isinstance(py_val, (int, float, str)):
    raise error.Expr(
        'Expected string-like value (Bool, Int, Str), but got %s' % type(py_val),
        loc.WordPart(word_part))

  return str(py_val)


# XXX this function should be removed once _EvalExpr is completeley refactored.
# Until then we'll need this as a bit of scaffolding to allow us to refactor one
# kind of expression at a time while still being able to type-check and run
# tests.
def _PyObjToValue(val):
  # type: (Any) -> value_t

  if val is None:
    return value.Undef()

  elif isinstance(val, bool):
    return value.Bool(val)

  elif isinstance(val, int):
    return value.Int(val)

  elif isinstance(val, float):
    return value.Float(val)

  elif isinstance(val, str):
    return value.Str(val)

  elif isinstance(val, list):
    return value.List(val)

  elif isinstance(val, dict):
    return value.Dict(val)

  else:
    raise NotImplementedError()


def _ValueToPyObj(val):
  # type: (value_t) -> Any

  UP_val = val
  with tagswitch(val) as case:
    if case(value_e.Undef):
      return None

    elif case(value_e.Bool):
      val = cast(value.Bool, UP_val)
      return val.b

    elif case(value_e.Int):
      val = cast(value.Int, UP_val)
      return val.i

    elif case(value_e.Float):
      val = cast(value.Float, UP_val)
      return val.f

    elif case(value_e.Str):
      val = cast(value.Str, UP_val)
      return val.s

    elif case(value_e.MaybeStrArray):
      val = cast(value.MaybeStrArray, UP_val)
      # XXX type checker is somehow OK with this (holes)?
      return objects.StrArray(val.strs)

    elif case(value_e.List):
      val = cast(value.List, UP_val)
      return val.items

    elif case(value_e.AssocArray):
      val = cast(value.AssocArray, UP_val)
      return val.d

    elif case(value_e.Dict):
      val = cast(value.Dict, UP_val)
      return val.d

    else:
      raise NotImplementedError()
  

class OilEvaluator(object):
  """Shared between arith and bool evaluators.

  They both:

  1. Convert strings to integers, respecting shopt -s strict_arith.
  2. Look up variables and evaluate words.
  """

  def __init__(self,
               mem,  # type: Mem
               mutable_opts,  # type: state.MutableOpts
               funcs,  # type: Dict[str, Any]
               splitter,  # type: split.SplitContext
               errfmt,  # type: ErrorFormatter
               ):
    # type: (...) -> None
    self.shell_ex = None  # type: _Executor
    self.word_ev = None  # type: AbstractWordEvaluator

    self.mem = mem
    self.mutable_opts = mutable_opts
    self.funcs = funcs
    self.splitter = splitter
    self.errfmt = errfmt

  def CheckCircularDeps(self):
    # type: () -> None
    assert self.shell_ex is not None
    assert self.word_ev is not None

  def LookupVar(self, name, var_loc):
    # type: (str, loc_t) -> Any
    return LookupVar(self.mem, name, scope_e.LocalOrGlobal, var_loc)

  def EvalPlusEquals(self, lval, rhs_py):
    # type: (lvalue.Named, Union[int, float]) -> Union[int, float]
    lhs_py = self.LookupVar(lval.name, loc.Missing())

    if not isinstance(lhs_py, (int, float)):
      # TODO: Could point at the variable name
      e_die("Object of type %r doesn't support +=" % lhs_py.__class__.__name__)

    return lhs_py + rhs_py

  def EvalLHS(self, node):
    # type: (expr_t) -> lvalue_t
    if 0:
      print('EvalLHS()')
      node.PrettyPrint()
      print('')

    UP_node = node
    with tagswitch(node) as case:
      if case(expr_e.Var):
        node = cast(expr.Var, UP_node)
        return location.LName(node.name.tval)
      else:
        # TODO:
        # subscripts, tuple unpacking, starred expressions, etc.
        raise NotImplementedError(node.__class__.__name__)

  # Copied from BoolEvaluator
  def _EvalMatch(self, left, right, set_match_result):
    # type: (str, Any, bool) -> bool
    """
    Args:
      set_match_result: Whether to assign
    """
    if isinstance(right, str):
      pass
    elif isinstance(right, objects.Regex):
      right = right.AsPosixEre()
    else:
      raise RuntimeError(
          "RHS of ~ should be string or Regex (got %s)" % right.__class__.__name__)
    
    # TODO:
    # - libc_regex_match should populate _start() and _end() too (out params?)
    # - What is the ordering for named captures?  See demo/ere*.sh

    matches = libc.regex_match(right, left)
    if matches:
      if set_match_result:
        self.mem.SetMatches(matches)
      return True
    else:
      if set_match_result:
        self.mem.ClearMatches()
      return False

  def EvalArgList(self, args):
    # type: (ArgList) -> Tuple[List[Any], Dict[str, Any]]
    """ Used by f(x) and echo $f(x). """
    pos_args = []
    for arg in args.positional:
      UP_arg = arg

      if arg.tag() == expr_e.Spread:
        arg = cast(expr.Spread, UP_arg)
        # assume it returns a list
        pos_args.extend(self.EvalExpr(arg.child, loc.Missing()))
      else:
        pos_args.append(self.EvalExpr(arg, loc.Missing()))

    kwargs = {}
    for named in args.named:
      if named.name:
        kwargs[named.name.tval] = self.EvalExpr(named.value, loc.Missing())
      else:
        # ...named
        kwargs.update(self.EvalExpr(named.value, loc.Missing()))
    return pos_args, kwargs

  def _EvalIndices(self, indices):
    # type: (List[expr_t]) -> Any
    if len(indices) == 1:
      return self.EvalExpr(indices[0], loc.Missing())
    else:
      # e.g. mydict[a,b]
      return tuple(self.EvalExpr(ind, loc.Missing()) for ind in indices)

  def EvalPlaceExpr(self, place):
    # type: (place_expr_t) -> lvalue_t

    UP_place = place
    with tagswitch(place) as case:
      if case(place_expr_e.Var):
        place = cast(place_expr.Var, UP_place)

        return location.LName(place.name.tval)

      elif case(place_expr_e.Subscript):
        place = cast(Subscript, UP_place)

        obj = self.EvalExpr(place.obj, loc.Missing())
        index = self._EvalIndices(place.indices)
        return lvalue.ObjIndex(obj, index)

      elif case(place_expr_e.Attribute):
        place = cast(Attribute, UP_place)

        obj = self.EvalExpr(place.obj, loc.Missing())
        if place.op.id == Id.Expr_RArrow:
          index = place.attr.tval
          return lvalue.ObjIndex(obj, index)
        else:
          return lvalue.ObjAttr(obj, place.attr.tval)

      else:
        raise NotImplementedError(place)

  def EvalExprSub(self, part):
    # type: (word_part.ExprSub) -> part_value_t
    py_val = self.EvalExpr(part.child, loc.Missing())
    s = Stringify(py_val, word_part=part)
    return part_value.String(s, False, False)

  def EvalInlineFunc(self, part):
    # type: (word_part.FuncCall) -> part_value_t
    func_name = part.name.tval[1:]

    fn_val = self.mem.GetValue(func_name)  # type: value_t
    if fn_val.tag() != value_e.Obj:
      e_die("Expected function named %r, got %r " % (func_name, fn_val))
    assert isinstance(fn_val, value.Obj)

    func = fn_val.obj
    pos_args, named_args = self.EvalArgList(part.args)

    try:
      id_ = part.name.id
      if id_ == Id.VSub_DollarName:
        # func() can raise TypeError, ValueError, etc.
        s = Stringify(func(*pos_args, **named_args), word_part=part)
        part_val = part_value.String(s, False, False)  # type: part_value_t

      elif id_ == Id.Lit_Splice:
        # func() can raise TypeError, ValueError, etc.
        # 'for in' raises TypeError if it's not iterable
        a = [
            Stringify(item, word_part=part)
            for item in func(*pos_args, **named_args)
            ]
        part_val = part_value.Array(a)

      else:
        raise AssertionError(id_)

    # Same error handling as EvalExpr below
    except TypeError as e:
      # TODO: Add location info.  Right now we blame the variable name for
      # 'var' and 'setvar', etc.
      raise error.Expr('Type error in expression: %s' % str(e), loc.Missing())
    except (AttributeError, ValueError) as e:
      raise error.Expr('Expression eval error: %s' % str(e), loc.Missing())

    return part_val

  def SpliceValue(self, val, part):
    # type: (value.Obj, word_part.Splice) -> List[Any]
    try:
      items = [Stringify(item, word_part=part) for item in val.obj]
    except TypeError as e:  # TypeError if it isn't iterable
      raise error.Expr('Type error in expression: %s' % str(e),
                       loc.WordPart(part))

    return items

  def EvalExpr(self, node, blame_loc):
    # type: (expr_t, loc_t) -> Any
    """Public API for _EvalExpr that ensures that command_sub_errexit is on."""
    try:
      with state.ctx_OilExpr(self.mutable_opts):
        return self._EvalExpr(node)
    except TypeError as e:
      raise error.Expr('Type error in expression: %s' % str(e), blame_loc)
    except (AttributeError, ValueError) as e:
      raise error.Expr('Expression eval error: %s' % str(e), blame_loc)

    # Note: IndexError and KeyError are handled in more specific places

  def _ToNumber(self, val):
    # type: (Any) -> Union[int, float]
    """Convert to something that can be compared.
    """
    if isinstance(val, bool):
      raise ValueError("A boolean isn't a number")  # preserves location

    if isinstance(val, int):
      return val

    if isinstance(val, float):
      return val

    if isinstance(val, str):
      # NOTE: Can we avoid scanning the string twice?
      if match.LooksLikeInteger(val):
        return int(val)
      elif match.LooksLikeFloat(val):
        return float(val)
      else:
        raise ValueError("%r doesn't look like a number" % val)

    raise ValueError("%r isn't like a number" % (val,))

  def _ToInteger(self, val):
    # type: (Any) -> int
    """Like the above, but no floats.
    """
    if isinstance(val, bool):
      raise ValueError("A boolean isn't an integer")  # preserves location

    if isinstance(val, int):
      return val

    if isinstance(val, str):
      # NOTE: Can we avoid scanning the string twice?
      if match.LooksLikeInteger(val):
        return int(val)
      else:
        raise ValueError("%r doesn't look like an integer" % val)

    raise ValueError("%r isn't like an integer" % (val,))

  def _ValueToInteger(self, val):
    # type: (value_t) -> int
    UP_val = val
    with tagswitch(val) as case:
      if case(value_e.Int):
        val = cast(value.Int, UP_val)
        return val.i

      elif case(value_e.Str):
        val = cast(value.Str, UP_val)
        if match.LooksLikeInteger(val.s):
          return int(val.s)
        else:
          raise ValueError("%r doesn't look like an integer" % val.s)

    raise error.InvalidType('Expected Int', loc.Missing())

  def _ValueToNumber(self, val):
    # type: (value_t) -> value_t
    """
    If val is a number-looking string, it will be converted to the appropriate
    type. Otherwise val is returned untouched.
    """ 
    UP_val = val
    with tagswitch(val) as case:
      if case(value_e.Str):
        val = cast(value.Str, UP_val)
        if match.LooksLikeInteger(val.s):
          return value.Int(int(val.s))

        if match.LooksLikeFloat(val.s):
          return value.Float(float(val.s))

    return val
    
  def _EvalConst(self, node):
    # type: (expr.Const) -> value_t

    # Remove underscores from 1_000_000.  The lexer is responsible for
    # validation.  TODO: Do this at PARSE TIME / COMPILE TIME.

    c = node.c.tval.replace('_', '')

    id_ = node.c.id
    if id_ == Id.Expr_DecInt:
      return value.Int(int(c))
    if id_ == Id.Expr_BinInt:
      return value.Int(int(c, 2))
    if id_ == Id.Expr_OctInt:
      return value.Int(int(c, 8))
    if id_ == Id.Expr_HexInt:
      return value.Int(int(c, 16))

    if id_ == Id.Expr_Float:
      return value.Float(float(c))

    if id_ == Id.Expr_Null:
      return value.Undef()
    if id_ == Id.Expr_True:
      return value.Bool(True)
    if id_ == Id.Expr_False:
      return value.Bool(False)

    if id_ == Id.Expr_Name:
      # for {name: 'bob'}
      # Maybe also :Symbol?
      return value.Str(node.c.tval)

    # These calculations could also be done at COMPILE TIME
    if id_ == Id.Char_OneChar:
      return value.Int(consts.LookupCharInt(node.c.tval[1]))  # It's an integer
    if id_ == Id.Char_UBraced:
      s = node.c.tval[3:-1]  # \u{123}
      return value.Int(int(s, 16))
    if id_ == Id.Char_Pound:
      # TODO: accept UTF-8 code point instead of single byte
      byte = node.c.tval[2]  # the a in #'a'
      return value.Int(ord(byte))  # It's an integer

    # NOTE: We could allow Ellipsis for a[:, ...] here, but we're not using it
    # yet.
    raise AssertionError(id_)

  def _EvalCommandSub(self, node):
    # type: (CommandSub) -> value_t

    id_ = node.left_token.id
    # &(echo block literal)
    if id_ == Id.Left_CaretParen:
      return value.Str('TODO: value.Block')
    else:
      stdout = self.shell_ex.RunCommandSub(node)
      if id_ == Id.Left_AtParen:  # @(seq 3)
        strs = self.splitter.SplitForWordEval(stdout)
        return value.MaybeStrArray(strs)
      else:
        return value.Str(stdout)

  def _EvalShArrayLiteral(self, node):
    # type: (ShArrayLiteral) -> value_t
    words = braces.BraceExpandWords(node.words)
    strs = self.word_ev.EvalWordSequence(words)
    #log('ARRAY LITERAL EVALUATED TO -> %s', strs)
    return value.MaybeStrArray(strs)

  def _EvalDoubleQuoted(self, node):
    # type: (DoubleQuoted) -> value_t

    # In an ideal world, I would *statically* disallow:
    # - "$@" and "${array[@]}"
    # - backticks like `echo hi`
    # - $(( 1+2 )) and $[] -- although useful for refactoring
    #   - not sure: ${x%%} -- could disallow this
    #     - these enters the ArgDQ state: "${a:-foo bar}" ?
    # But that would complicate the parser/evaluator.  So just rely on
    # strict_array to disallow the bad parts.
    return value.Str(self.word_ev.EvalDoubleQuotedToString(node))

  def _EvalSingleQuoted(self, node):
    # type: (SingleQuoted) -> value_t
    return value.Str(word_compile.EvalSingleQuoted(node))

  def _EvalBracedVarSub(self, node):
    # type: (BracedVarSub) -> value_t
    return value.Str(self.word_ev.EvalBracedVarSubToString(node))

  def _EvalSimpleVarSub(self, node):
    # type: (SimpleVarSub) -> value_t
    return value.Str(self.word_ev.EvalSimpleVarSubToString(node))

  def _EvalUnary(self, node):
    # type: (expr.Unary) -> value_t
    child = _PyObjToValue(self._EvalExpr(node.child)) # XXX
    if node.op.id == Id.Arith_Minus:
      UP_child = child
      with tagswitch(child) as case:
        if case(value_e.Int):
          child = cast(value.Int, UP_child)
          return value.Int(-child.i)

        elif case(value_e.Float):
          child = cast(value.Float, UP_child)
          return value.Float(-child.f)

        else:
          # TODO: want location of operand
          raise error.InvalidType('Expected Int or Float', loc.Missing())

    if node.op.id == Id.Arith_Tilde:
      UP_child = child
      with tagswitch(child) as case:
        if case(value_e.Int):
          child = cast(value.Int, UP_child)
          return value.Int(~child.i)

        else:
          # TODO: want location of operand
          raise error.InvalidType('Expected Int', loc.Missing())

    if node.op.id == Id.Expr_Not:
      UP_child = child
      with tagswitch(child) as case:
        if case(value_e.Bool):
          child = cast(value.Bool, UP_child)
          return value.Bool(not child.b)

        else:
          # TODO: want location of operand
          raise error.InvalidType('Expected Bool', loc.Missing())

    raise NotImplementedError(node.op.id)

  def _ArithNumeric(self, left, right, op):
    # type: (value_t, value_t, Id_t) -> value_t
    left = self._ValueToNumber(left)
    right = self._ValueToNumber(right)
    UP_left = left
    UP_right = right

    with tagswitch(left) as lcase:
      if lcase(value_e.Int):
        left = cast(value.Int, UP_left)

        with tagswitch(right) as rcase:
          if rcase(value_e.Int):
            right = cast(value.Int, UP_right)

            if op == Id.Arith_Plus:
              return value.Int(left.i + right.i)
            elif op == Id.Arith_Minus:
              return value.Int(left.i - right.i)
            elif op == Id.Arith_Star:
              return value.Int(left.i * right.i)
            elif op == Id.Arith_Slash:
              if right.i == 0:
                raise ZeroDivisionError()

              return value.Float(left.i / float(right.i))
            else:
              raise NotImplementedError(op)

          elif rcase(value_e.Float):
            right = cast(value.Float, UP_right)
            if op == Id.Arith_Plus:
              return value.Float(left.i + right.f)
            elif op == Id.Arith_Minus:
              return value.Float(left.i - right.f)
            elif op == Id.Arith_Star:
              return value.Float(left.i * right.f)
            elif op == Id.Arith_Slash:
              if right.f == 0.0:
                raise ZeroDivisionError()

              return value.Float(left.i / right.f)
            else:
              raise NotImplementedError(op)

          else:
            raise error.InvalidType('Expected Int or Float', loc.Missing())

      elif lcase(value_e.Float):
        left = cast(value.Float, UP_left)

        with tagswitch(right) as rcase:
          if rcase(value_e.Int):
            right = cast(value.Int, UP_right)
            if op == Id.Arith_Plus:
              return value.Float(left.f + right.i)
            elif op == Id.Arith_Minus:
              return value.Float(left.f - right.i)
            elif op == Id.Arith_Star:
              return value.Float(left.f * right.i)
            elif op == Id.Arith_Slash:
              if right.i == 0:
                raise ZeroDivisionError()

              return value.Float(left.f / right.i)
            else:
              raise NotImplementedError(op)

          elif rcase(value_e.Float):
            right = cast(value.Float, UP_right)
            if op == Id.Arith_Plus:
              return value.Float(left.f + right.f)
            elif op == Id.Arith_Minus:
              return value.Float(left.f - right.f)
            elif op == Id.Arith_Star:
              return value.Float(left.f * right.f)
            elif op == Id.Arith_Slash:
              if right.f == 0.0:
                raise ZeroDivisionError()

              return value.Float(left.f / right.f)
            else:
              raise NotImplementedError(op)

          else:
            raise error.InvalidType('Expected Int or Float', loc.Missing())

      else:
          raise error.InvalidType('Expected Int or Float', loc.Missing())

  def _ArithDivideInt(self, left, right):
    # type: (value_t, value_t) -> value.Int
    left_i = self._ValueToInteger(left)
    right_i = self._ValueToInteger(right)
    if right_i == 0:
      raise ZeroDivisionError()

    return value.Int(left_i // right_i)

  def _ArithModulus(self, left, right):
    # type: (value_t, value_t) -> value.Int
    left_i = self._ValueToInteger(left)
    right_i = self._ValueToInteger(right)
    if right_i == 0:
      raise ZeroDivisionError()

    return value.Int(left_i % right_i)

  def _ArithExponentiate(self, left, right):
    # type: (value_t, value_t) -> value.Int
    left_i = self._ValueToInteger(left)
    right_i = self._ValueToInteger(right)
    return value.Int(left_i ** right_i)

  def _ArithBitwise(self, left, right, op):
    # type: (value_t, value_t, Id_t) -> value.Int
    left_i = self._ValueToInteger(left)
    right_i = self._ValueToInteger(right)

    if op == Id.Arith_Amp:
      return value.Int(left_i & right_i)
    elif op == Id.Arith_Pipe:
      return value.Int(left_i | right_i)
    elif op == Id.Arith_Caret:
      return value.Int(left_i ^ right_i)
    elif op == Id.Arith_DGreat:
      return value.Int(left_i >> right_i)
    elif op == Id.Arith_DLess:
      return value.Int(left_i << right_i)

    raise NotImplementedError()

  def _ArithLogical(self, left, right, op):
    # type: (value_t, value_t, Id_t) -> value.Bool
    UP_left = left
    UP_right = right

    with tagswitch(left) as lcase:
      if lcase(value_e.Bool):
        left = cast(value.Bool, UP_left)

        with tagswitch(right) as rcase:
          if rcase(value_e.Bool):
            right = cast(value.Bool, UP_right)

            if op == Id.Expr_And:
              return value.Bool(left.b and right.b)
            elif op == Id.Expr_Or:
              return value.Bool(left.b or right.b)

          else:
            raise error.InvalidType('Expected Bool', loc.Missing())

      else:
        raise error.InvalidType('Expected Bool', loc.Missing())

      raise NotImplementedError()

  def _Concat(self, left, right):
    # type: (value_t, value_t) -> value_t
    UP_left = left
    UP_right = right

    with tagswitch(left) as lcase:
      if lcase(value_e.List):
        left = cast(value.List, UP_left)

        with tagswitch(right) as rcase:
          if rcase(value_e.List):
            right = cast(value.List, UP_right)
            return value.List(left.items + right.items)

          else:
            raise error.InvalidType('Expected List', loc.Missing())

      if lcase(value_e.Str):
        left = cast(value.Str, UP_left)
        with tagswitch(right) as rcase:
          if rcase(value_e.Str):
            right = cast(value.Str, UP_right)
            return value.Str(left.s + right.s)

          else:
            raise error.InvalidType('Expected String', loc.Missing())

      if lcase(value_e.MaybeStrArray):
        left = cast(value.MaybeStrArray, UP_left)
        with tagswitch(right) as rcase:
          if rcase(value_e.MaybeStrArray):
            right = cast(value.MaybeStrArray, UP_right)
            return value.MaybeStrArray(left.strs + right.strs)

          else:
            raise error.InvalidType('Expected MaybeStrArray', loc.Missing())

      else:
        raise error.InvalidType('Expected List or String', loc.Missing())

  def _EvalBinary(self, node):
    # type: (expr.Binary) -> value_t

    left = _PyObjToValue(self._EvalExpr(node.left))
    right = _PyObjToValue(self._EvalExpr(node.right))

    if node.op.id in \
      (Id.Arith_Plus, Id.Arith_Minus, Id.Arith_Star, Id.Arith_Slash):
      try:
        return self._ArithNumeric(left, right, node.op.id)
      except ZeroDivisionError:
        raise error.Expr('divide by zero', node.op)

    if node.op.id == Id.Expr_DSlash:
      return self._ArithDivideInt(left, right)
    if node.op.id == Id.Arith_Percent:
      return self._ArithModulus(left, right)

    if node.op.id == Id.Arith_DStar:  # Exponentiation
      return self._ArithExponentiate(left, right)

    if node.op.id == Id.Arith_DPlus:
      # list or string concatenation
      # dicts can have duplicates, so don't mess with that
      return self._Concat(left, right)

    # Bitwise
    if node.op.id in \
      (Id.Arith_Amp, Id.Arith_Pipe, Id.Arith_Caret, Id.Arith_DGreat, Id.Arith_DLess):
      return self._ArithBitwise(left, right, node.op.id)

    # Logical
    if node.op.id in (Id.Expr_And, Id.Expr_Or):
      return self._ArithLogical(left, right, node.op.id)

    raise NotImplementedError(node.op.id)

  def _EvalRange(self, node):
    # type: (expr.Range) -> Any # XXX

    lower = self._EvalExpr(node.lower)
    upper = self._EvalExpr(node.upper)
    return xrange(lower, upper)

  def _EvalSlice(self, node):
    # type: (expr.Slice) -> Any # XXX

    lower = self._EvalExpr(node.lower) if node.lower else None
    upper = self._EvalExpr(node.upper) if node.upper else None
    return slice(lower, upper)

  def _EvalCompare(self, node):
    # type: (expr.Compare) -> Any # XXX

    left = self._EvalExpr(node.left)
    result = True  # Implicit and
    for op, right_expr in zip(node.ops, node.comparators):

      right = self._EvalExpr(right_expr)

      if op.id == Id.Arith_Less:
        result = self._ToNumber(left) < self._ToNumber(right)
      elif op.id == Id.Arith_Great:
        result = self._ToNumber(left) > self._ToNumber(right)
      elif op.id == Id.Arith_LessEqual:
        result = self._ToNumber(left) <= self._ToNumber(right)
      elif op.id == Id.Arith_GreatEqual:
        result = self._ToNumber(left) >= self._ToNumber(right)

      elif op.id == Id.Expr_TEqual:
        result = left == right
      elif op.id == Id.Expr_NotDEqual:
        result = left != right

      elif op.id == Id.Expr_In:
        result = left in right
      elif op.id == Id.Node_NotIn:
        result = left not in right

      elif op.id == Id.Expr_Is:
        result = left is right
      elif op.id == Id.Node_IsNot:
        result = left is not right

      elif op.id == Id.Expr_DTilde:
        # no extglob in Oil language; use eggex
        return libc.fnmatch(right, left)
      elif op.id == Id.Expr_NotDTilde:
        return not libc.fnmatch(right, left)

      elif op.id == Id.Expr_TildeDEqual:
        # Approximate equality
        if not isinstance(left, str):
          e_die('~== expects a string on the left', op)

        left = left.strip()
        if isinstance(right, str):
          return left == right

        if isinstance(right, bool):  # Python quirk: must come BEFORE int
          left = left.lower()
          if left in ('true', '1'):
            left2 = True
          elif left in ('false', '0'):
            left2 = False
          else:
            return False

          log('left %r left2 %r', left, left2)
          return left2 == right

        if isinstance(right, int):
          if not left.isdigit():
            return False
          return int(left) == right

        e_die('~== expects Str, Int, or Bool on the right', op)

      else:
        try:
          if op.id == Id.Arith_Tilde:
            result = self._EvalMatch(left, right, True)

          elif op.id == Id.Expr_NotTilde:
            result = not self._EvalMatch(left, right, False)

          else:
            raise AssertionError(op)
        except RuntimeError as e:
          # Status 2 indicates a regex parse error.  This is fatal in OSH but
          # not in bash, which treats [[ like a command with an exit code.
          e_die_status(2, 'Invalid regex %r' % right, op)

      if not result:
        return result

      left = right

    return result

  def _EvalIfExp(self, node):
    # type: (expr.IfExp) -> Any # XXX
    b = self._EvalExpr(node.test)
    if b:
      return self._EvalExpr(node.body)
    else:
      return self._EvalExpr(node.orelse)

  def _EvalList(self, node):
    # type: (expr.List) -> Any # XXX
    return [self._EvalExpr(e) for e in node.elts]

  def _EvalTuple(self, node):
    # type: (expr.Tuple) -> Any # XXX
    return tuple(self._EvalExpr(e) for e in node.elts)

  def _EvalDict(self, node):
    # type: (expr.Dict) -> Any # XXX
    # NOTE: some keys are expr.Const
    keys = [self._EvalExpr(e) for e in node.keys]

    values = []
    for i, value_expr in enumerate(node.values):
      if value_expr.tag() == expr_e.Implicit:
        v = self.LookupVar(keys[i], loc.Missing())  # {name}
      else:
        v = self._EvalExpr(value_expr)
      values.append(v)

    d = NewDict()
    for k, v in zip(keys, values):
      d[k] = v
    return d

  def _EvalFuncCall(self, node):
    # type: (expr.FuncCall) -> Any # XXX
    func = self._EvalExpr(node.func)
    pos_args, named_args = self.EvalArgList(node.args)
    ret = func(*pos_args, **named_args)
    return ret

  def _EvalSubscript(self, node):
    # type: (Subscript) -> Any # XXX
    obj = self._EvalExpr(node.obj)
    index = self._EvalIndices(node.indices)
    try:
      result = obj[index]
    except KeyError:
      # TODO: expr.Subscript has no error location
      raise error.Expr('dict entry not found', loc.Missing())
    except IndexError:
      # TODO: expr.Subscript has no error location
      raise error.Expr('index out of range', loc.Missing())

    return result

  def _EvalAttribute(self, node):
    # type: (Attribute) -> Any # XXX
    o = self._EvalExpr(node.obj)
    id_ = node.op.id
    if id_ == Id.Expr_Dot:
      # Used for .startswith()
      name = node.attr.tval
      return getattr(o, name)

    if id_ == Id.Expr_RArrow:  # d->key is like d['key']
      name = node.attr.tval
      try:
        result = o[name]
      except KeyError:
        raise error.Expr('dict entry not found', node.op)

      return result

    if id_ == Id.Expr_DColon:  # StaticName::member
      raise NotImplementedError(id_)

      # TODO: We should prevent virtual lookup here?  This is a pure static
      # namespace lookup?
      # But Python doesn't any hook for this.
      # Maybe we can just check that it's a module?  And modules don't lookup
      # in a supertype or __class__, etc.

    raise AssertionError(id_)

  def _EvalExpr(self, node):
    # type: (expr_t) -> Any
    """
    This is a naive PyObject evaluator!  It uses the type dispatch of the host
    Python interpreter.

    Returns:
      A Python object of ANY type.  Should be wrapped in value.Obj() for
      storing in Mem.
    """
    if 0:
      print('_EvalExpr()')
      node.PrettyPrint()
      print('')

    UP_node = node
    with tagswitch(node) as case:
      if case(expr_e.Const):
        node = cast(expr.Const, UP_node)

        return _ValueToPyObj(self._EvalConst(node))

      elif case(expr_e.Var):
        node = cast(expr.Var, UP_node)

        return self.LookupVar(node.name.tval, var_loc=loc.Span(node.name.span_id))

      elif case(expr_e.CommandSub):
        node = cast(CommandSub, UP_node)

        return _ValueToPyObj(self._EvalCommandSub(node))

      elif case(expr_e.ShArrayLiteral):
        node = cast(ShArrayLiteral, UP_node)
        return _ValueToPyObj(self._EvalShArrayLiteral(node))

      elif case(expr_e.DoubleQuoted):
        node = cast(DoubleQuoted, UP_node)
        return _ValueToPyObj(self._EvalDoubleQuoted(node))

      elif case(expr_e.SingleQuoted):
        node = cast(SingleQuoted, UP_node)
        return _ValueToPyObj(self._EvalSingleQuoted(node))

      elif case(expr_e.BracedVarSub):
        node = cast(BracedVarSub, UP_node)
        return _ValueToPyObj(self._EvalBracedVarSub(node))

      elif case(expr_e.SimpleVarSub):
        node = cast(SimpleVarSub, UP_node)
        return _ValueToPyObj(self._EvalSimpleVarSub(node))

      elif case(expr_e.Unary):
        node = cast(expr.Unary, UP_node)
        return _ValueToPyObj(self._EvalUnary(node))

      elif case(expr_e.Binary):
        node = cast(expr.Binary, UP_node)
        return _ValueToPyObj(self._EvalBinary(node))

      elif case(expr_e.Range):  # 1:10  or  1:10:2
        node = cast(expr.Range, UP_node)
        return self._EvalRange(node)

      elif case(expr_e.Slice):  # a[:0]
        node = cast(expr.Slice, UP_node)
        return self._EvalSlice(node)

      elif case(expr_e.Compare):
        node = cast(expr.Compare, UP_node)
        return self._EvalCompare(node)
   
      elif case(expr_e.IfExp):
        node = cast(expr.IfExp, UP_node)
        return self._EvalIfExp(node)

      elif case(expr_e.List):
        node = cast(expr.List, UP_node)
        return self._EvalList(node)

      elif case(expr_e.Tuple):
        node = cast(expr.Tuple, UP_node)
        return self._EvalTuple(node)

      elif case(expr_e.Dict):
        node = cast(expr.Dict, UP_node)
        return self._EvalDict(node)

      elif case(expr_e.ListComp):
        e_die_status(2, 'List comprehension reserved but not implemented')

        #
        # TODO: Move this code to the new for loop
        #

        # TODO:
        # - Consolidate with command_e.OilForIn in osh/cmd_eval.py?
        # - Do I have to push a temp frame here?
        #   Hm... lexical or dynamic scope is an issue.
        result = []
        comp = node.generators[0]
        obj = self._EvalExpr(comp.iter)

        # TODO: Handle x,y etc.
        iter_name = comp.lhs[0].name.tval

        if isinstance(obj, str):
          e_die("Strings aren't iterable")
        else:
          it = obj.__iter__()

        while True:
          try:
            loop_val = it.next()  # e.g. x
          except StopIteration:
            break
          self.mem.SetValue(
              location.LName(iter_name), value.Obj(loop_val), scope_e.LocalOnly)

          if comp.cond:
            b = self._EvalExpr(comp.cond)
          else:
            b = True

          if b:
            item = self._EvalExpr(node.elt)  # e.g. x*2
            result.append(item)

        return result

      elif case(expr_e.GeneratorExp):
        e_die_status(2, 'Generator expression reserved but not implemented')

      elif case(expr_e.Lambda):  # |x| x+1 syntax is reserved
        # TODO: Location information for |, or func
        # Note: anonymous functions also evaluate to a Lambda, but they shouldn't
        e_die_status(2, 'Lambda reserved but not implemented')

      elif case(expr_e.FuncCall):
        node = cast(expr.FuncCall, UP_node)
        return self._EvalFuncCall(node)

      elif case(expr_e.Subscript):
        node = cast(Subscript, UP_node)
        return self._EvalSubscript(node)

      # Note: This is only for the obj.method() case.  We will probably change
      # the AST and get rid of getattr().
      elif case(expr_e.Attribute):  # obj.attr 
        node = cast(Attribute, UP_node)
        return self._EvalAttribute(node)

      elif case(expr_e.RegexLiteral):
        node = cast(expr.RegexLiteral, UP_node)

        # TODO: Should this just be an object that ~ calls?
        return objects.Regex(self.EvalRegex(node.regex))

      else:
        raise NotImplementedError(node.__class__.__name__)

  def _EvalClassLiteralTerm(self, term, out):
    # type: (class_literal_term_t, List[char_class_term_t]) -> None
    UP_term = term

    s = None  # type: str
    spid = runtime.NO_SPID

    with tagswitch(term) as case:

      if case(class_literal_term_e.CharLiteral):
        term = cast(class_literal_term.CharLiteral, UP_term)

        # What about \0?
        # At runtime, ERE should disallow it.  But we can also disallow it here.
        out.append(word_compile.EvalCharLiteralForRegex(term.tok))
        return

      elif case(class_literal_term_e.Range):
        term = cast(class_literal_term.Range, UP_term)

        cp_start = word_compile.EvalCharLiteralForRegex(term.start)
        cp_end = word_compile.EvalCharLiteralForRegex(term.end)
        out.append(char_class_term.Range(cp_start, cp_end))
        return

      elif case(class_literal_term_e.PosixClass):
        term = cast(PosixClass, UP_term)
        out.append(term)
        return

      elif case(class_literal_term_e.PerlClass):
        term = cast(PerlClass, UP_term)
        out.append(term)
        return

      elif case(class_literal_term_e.SingleQuoted):
        term = cast(SingleQuoted, UP_term)

        s = word_compile.EvalSingleQuoted(term)
        spid = term.left.span_id

      elif case(class_literal_term_e.DoubleQuoted):
        term = cast(DoubleQuoted, UP_term)

        s = self.word_ev.EvalDoubleQuotedToString(term)
        spid = term.left.span_id

      elif case(class_literal_term_e.BracedVarSub):
        term = cast(BracedVarSub, UP_term)

        s = self.word_ev.EvalBracedVarSubToString(term)
        spid = term.left.span_id

      elif case(class_literal_term_e.SimpleVarSub):
        term = cast(SimpleVarSub, UP_term)

        s = self.word_ev.EvalSimpleVarSubToString(term)
        spid = term.left.span_id

    assert s is not None, term
    for ch in s:
      char_int = ord(ch)
      if char_int >= 128:
        # / [ '\x7f\xff' ] / is better written as / [ \x7f \xff ] /
        e_die("Use unquoted char literal for byte %d, which is >= 128"
              " (avoid confusing a set of bytes with a sequence)" % char_int,
              loc.Span(spid))
      out.append(CharCode(char_int, False, spid))

  def _EvalRegex(self, node):
    # type: (re_t) -> re_t
    """
    Resolve the references in an eggex, e.g. Hex and $const in
    
    / Hex '.' $const "--$const" /

    Some rules:

    * Speck/Token (syntactic concepts) -> Primitive (logical)
    * Splice -> Resolved
    * All Strings -> Literal
    """
    UP_node = node

    with tagswitch(node) as case:
      if case(re_e.Seq):
        node = cast(re.Seq, UP_node)
        new_children = [self._EvalRegex(child) for child in node.children]
        return re.Seq(new_children)

      elif case(re_e.Alt):
        node = cast(re.Alt, UP_node)
        new_children = [self._EvalRegex(child) for child in node.children]
        return re.Alt(new_children)

      elif case(re_e.Repeat):
        node = cast(re.Repeat, UP_node)
        return re.Repeat(self._EvalRegex(node.child), node.op)

      elif case(re_e.Group):
        node = cast(re.Group, UP_node)
        return re.Group(self._EvalRegex(node.child))

      elif case(re_e.Capture):  # Identical to Group
        node = cast(re.Capture, UP_node)
        return re.Capture(self._EvalRegex(node.child), node.var_name)

      elif case(re_e.CharClassLiteral):
        node = cast(re.CharClassLiteral, UP_node)

        new_terms = []  # type: List[char_class_term_t]
        for t in node.terms:
          # can get multiple char_class_term.CharCode for a
          # class_literal_term_t
          self._EvalClassLiteralTerm(t, new_terms)
        return re.CharClass(node.negated, new_terms)

      elif case(re_e.Token):
        node = cast(Token, UP_node)

        id_ = node.id
        val = node.tval

        if id_ == Id.Expr_Dot:
          return re.Primitive(Id.Re_Dot)

        if id_ == Id.Arith_Caret:  # ^
          return re.Primitive(Id.Re_Start)

        if id_ == Id.Expr_Dollar:  # $
          return re.Primitive(Id.Re_End)

        if id_ == Id.Expr_Name:
          if val == 'dot':
            return re.Primitive(Id.Re_Dot)
          raise NotImplementedError(val)

        if id_ == Id.Expr_Symbol:
          if val == '%start':
            return re.Primitive(Id.Re_Start)
          if val == '%end':
            return re.Primitive(Id.Re_End)
          raise NotImplementedError(val)

        # Must be Id.Char_{OneChar,Hex,Unicode4,Unicode8}
        kind = consts.GetKind(id_)
        assert kind == Kind.Char, id_
        s = word_compile.EvalCStringToken(node)
        return re.LiteralChars(s, node.span_id)

      elif case(re_e.SingleQuoted):
        node = cast(SingleQuoted, UP_node)

        s = word_compile.EvalSingleQuoted(node)
        return re.LiteralChars(s, node.left.span_id)

      elif case(re_e.DoubleQuoted):
        node = cast(DoubleQuoted, UP_node)

        s = self.word_ev.EvalDoubleQuotedToString(node)
        return re.LiteralChars(s, node.left.span_id)

      elif case(re_e.BracedVarSub):
        node = cast(BracedVarSub, UP_node)

        s = self.word_ev.EvalBracedVarSubToString(node)
        return re.LiteralChars(s, node.left.span_id)

      elif case(re_e.SimpleVarSub):
        node = cast(SimpleVarSub, UP_node)

        s = self.word_ev.EvalSimpleVarSubToString(node)
        return re.LiteralChars(s, node.left.span_id)

      elif case(re_e.Splice):
        node = cast(re.Splice, UP_node)

        obj = self.LookupVar(node.name.tval, var_loc=loc.Span(node.name.span_id))
        if not isinstance(obj, objects.Regex):
          e_die("Can't splice object of type %r into regex" % obj.__class__,
                node.name)
        # Note: we only splice the regex, and ignore flags.
        # Should we warn about this?
        return obj.regex

      else:
        # These are evaluated at translation time

        # case(re_e.PosixClass)
        # case(re_e.PerlClass)
        return node

  def EvalRegex(self, node):
    # type: (re_t) -> re_t
    """Trivial wrapper"""
    new_node = self._EvalRegex(node)

    # View it after evaluation
    if 0:
      log('After evaluation:')
      new_node.PrettyPrint()
      print()
    return new_node


