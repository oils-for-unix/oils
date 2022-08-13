#!/usr/bin/env python2
"""
expr_eval.py
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Kind
from _devbuild.gen.syntax_asdl import (
    place_expr_e, place_expr_t, place_expr__Var, attribute, subscript,

    speck, Token, 
    single_quoted, double_quoted, braced_var_sub, simple_var_sub,

    expr_e, expr_t, expr__Var, expr__Const, sh_array_literal, command_sub,
    expr__RegexLiteral, expr__Unary, expr__Binary, expr__Compare,
    expr__FuncCall, expr__IfExp, expr__Tuple, expr__List, expr__Dict,
    expr__Range, expr__Slice,
    expr__Spread,

    re, re_e, re_t, re__Splice, re__Seq, re__Alt, re__Repeat, re__Group,
    re__Capture, re__ClassLiteral,

    class_literal_term, class_literal_term_e, class_literal_term_t,
    class_literal_term__CharLiteral,

    word_part__ExprSub, word_part__FuncCall,
)
from _devbuild.gen.runtime_asdl import (
    scope_e, scope_t,
    part_value, part_value_t,
    lvalue,
    value, value_e, value_t,
    value__Str, value__MaybeStrArray, value__AssocArray, value__Obj
)
from asdl import runtime
from core import error
from core import state
from core.pyerror import e_die, e_die_status, log
from frontend import consts
from oil_lang import objects
from osh import braces
from osh import word_compile
from mycpp.mylib import NewDict, tagswitch

import libc

from typing import cast, Any, Dict, List, Union, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import (
      lvalue_t, lvalue__Named, # lvalue__ObjIndex, lvalue__ObjAttr,
  )
  from _devbuild.gen.syntax_asdl import ArgList
  from core.vm import _Executor
  from core.ui import ErrorFormatter
  from core.state import Mem
  from osh.word_eval import AbstractWordEvaluator
  from osh import split

_ = log


def LookupVar(mem, var_name, which_scopes, span_id=runtime.NO_SPID):
  # type: (Mem, str, scope_t, int) -> Any
  """Convert to a Python object so we can calculate on it natively."""

  # Lookup WITHOUT dynamic scope.
  val = mem.GetValue(var_name, which_scopes=which_scopes)
  if val.tag == value_e.Undef:
    # TODO: Location info
    e_die('Undefined variable %r', var_name, span_id=span_id)

  UP_val = val
  if val.tag == value_e.Str:
    val = cast(value__Str, UP_val)
    return val.s
  if val.tag == value_e.MaybeStrArray:
    val = cast(value__MaybeStrArray, UP_val)
    return val.strs  # node: has None
  if val.tag == value_e.AssocArray:
    val = cast(value__AssocArray, UP_val)
    return val.d
  if val.tag == value_e.Obj:
    val = cast(value__Obj, UP_val)
    return val.obj


def Stringify(py_val):
  # type: (Any) -> str
  """ For predictably converting between Python objects and strings.

  We don't want to tie our sematnics to the Python interpreter too much.
  """
  if isinstance(py_val, bool):
    return 'true' if py_val else 'false'  # Use JSON spelling

  if isinstance(py_val, objects.Regex):  # TODO: This should be a variant of value_t?
    return py_val.AsPosixEre()

  if not isinstance(py_val, (int, float, str)):
    # or float?
    e_die("Expected evaluation to Bool, Int, or Str.  Got %s", type(py_val))

  return str(py_val)


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

  def LookupVar(self, name, span_id=runtime.NO_SPID):
    # type: (str, int) -> Any
    return LookupVar(self.mem, name, scope_e.LocalOrGlobal, span_id=span_id)

  def EvalPlusEquals(self, lval, rhs_py):
    # type: (lvalue__Named, Union[int, float]) -> Union[int, float]
    lhs_py = self.LookupVar(lval.name)

    if not isinstance(lhs_py, (int, float)):
      # TODO: Could point at the variable name
      e_die("Object of type %r doesn't support +=", lhs_py.__class__.__name__)

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
        node = cast(expr__Var, UP_node)
        return lvalue.Named(node.name.val)
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
    # TODO: Rename EggEx?
    if isinstance(right, str):
      pass
    elif isinstance(right, objects.Regex):
      right = right.AsPosixEre()
    else:
      raise RuntimeError(
          "RHS of ~ should be string or Regex (got %s)" % right.__class__.__name__)
    
    # TODO: We need an API that can populate _start() and _end() too
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

      if arg.tag_() == expr_e.Spread:
        arg = cast(expr__Spread, UP_arg)
        # assume it returns a list
        pos_args.extend(self.EvalExpr(arg.child))
      else:
        pos_args.append(self.EvalExpr(arg))

    kwargs = {}
    for named in args.named:
      if named.name:
        kwargs[named.name.val] = self.EvalExpr(named.value)
      else:
        # ...named
        kwargs.update(self.EvalExpr(named.value))
    return pos_args, kwargs

  def _EvalIndices(self, indices):
    # type: (List[expr_t]) -> Any
    if len(indices) == 1:
      return self.EvalExpr(indices[0])
    else:
      # e.g. mydict[a,b]
      return tuple(self.EvalExpr(ind) for ind in indices)

  def EvalPlaceExpr(self, place):
    # type: (place_expr_t) -> lvalue_t

    UP_place = place
    with tagswitch(place) as case:
      if case(place_expr_e.Var):
        place = cast(place_expr__Var, UP_place)

        return lvalue.Named(place.name.val)

      elif case(place_expr_e.Subscript):
        place = cast(subscript, UP_place)

        obj = self.EvalExpr(place.obj)
        index = self._EvalIndices(place.indices)
        return lvalue.ObjIndex(obj, index)

      elif case(place_expr_e.Attribute):
        place = cast(attribute, UP_place)

        obj = self.EvalExpr(place.obj)
        if place.op.id == Id.Expr_RArrow:
          index = place.attr.val
          return lvalue.ObjIndex(obj, index)
        else:
          return lvalue.ObjAttr(obj, place.attr.val)

      else:
        raise NotImplementedError(place)

  def EvalExprSub(self, part):
    # type: (word_part__ExprSub) -> part_value_t
    py_val = self.EvalExpr(part.child)
    return part_value.String(Stringify(py_val))

  def EvalInlineFunc(self, part):
    # type: (word_part__FuncCall) -> part_value_t
    func_name = part.name.val[1:]

    fn_val = self.mem.GetValue(func_name)  # type: value_t
    if fn_val.tag != value_e.Obj:
      e_die("Expected function named %r, got %r ", func_name, fn_val)
    assert isinstance(fn_val, value__Obj)

    func = fn_val.obj
    pos_args, named_args = self.EvalArgList(part.args)

    id_ = part.name.id
    if id_ == Id.VSub_DollarName:
      s = Stringify(self._ApplyFunc(func, pos_args, named_args))
      part_val = part_value.String(s)  # type: part_value_t

    elif id_ == Id.Lit_Splice:
      # NOTE: Using iterable protocol as with @array.  TODO: Optimize
      # this so it doesn't make a copy?
      a = [Stringify(item) for item in self._ApplyFunc(func, pos_args, named_args)]
      part_val = part_value.Array(a)

    else:
      raise AssertionError(id_)

    return part_val

  def _ApplyFunc(self, func, pos_args, named_args):
    # type: (Any, Any, Any) -> Any
    """For inline function calls $strfunc(x) and @arrayfunc(x)"""
    try:
      return func(*pos_args, **named_args)

    # Same error handling as EvalExpr below
    except TypeError as e:
      # TODO: Add location info.  Right now we blame the variable name for
      # 'var' and 'setvar', etc.
      raise error.Expr('Type error in expression: %s' % str(e))
    except (AttributeError, ValueError) as e:
      raise error.Expr('Expression eval error: %s' % str(e))

  def EvalExpr(self, node, blame_spid=runtime.NO_SPID):
    # type: (expr_t, int) -> Any
    """Public API for _EvalExpr that ensures that command_sub_errexit is on."""
    try:
      with state.ctx_OilExpr(self.mutable_opts):
        return self._EvalExpr(node)
    except TypeError as e:
      # TODO: Add location info.  Right now we blame the variable name for
      # 'var' and 'setvar', etc.
      raise error.Expr('Type error in expression: %s' % str(e), span_id=blame_spid)
    except (AttributeError, ValueError) as e:
      raise error.Expr('Expression eval error: %s' % str(e), span_id=blame_spid)

    # Note: IndexError and KeyError are handled in more specific places

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
        node = cast(expr__Const, UP_node)

        # NOTE: This could all be done at PARSE TIME / COMPILE TIME.

        # Remove underscores from 1_000_000.  The lexer is responsible for
        # validation.
        c = node.c.val.replace('_', '')

        id_ = node.c.id
        if id_ == Id.Expr_DecInt:
          return int(c)
        if id_ == Id.Expr_BinInt:
          return int(c, 2)
        if id_ == Id.Expr_OctInt:
          return int(c, 8)
        if id_ == Id.Expr_HexInt:
          return int(c, 16)

        if id_ == Id.Expr_Float:
          return float(c)

        if id_ == Id.Expr_Null:
          return None
        if id_ == Id.Expr_True:
          return True
        if id_ == Id.Expr_False:
          return False

        if id_ == Id.Expr_Name:
          # for {name: 'bob'}
          # Maybe also :Symbol?
          return node.c.val

        # These two could be done at COMPILE TIME
        if id_ == Id.Char_OneChar:
          return consts.LookupCharInt(node.c.val[1])  # It's an integer
        if id_ == Id.Char_UBraced:
          s = node.c.val[3:-1]  # \u{123}
          return int(s, 16)
        if id_ == Id.Char_Pound:
          # TODO: accept UTF-8 code point instead of single byte
          byte = node.c.val[2]  # the a in #'a'
          return ord(byte)  # It's an integer

        # NOTE: We could allow Ellipsis for a[:, ...] here, but we're not using
        # it yet.
        raise AssertionError(id_)

      elif case(expr_e.Var):
        node = cast(expr__Var, UP_node)

        return self.LookupVar(node.name.val, span_id=node.name.span_id)

      elif case(expr_e.CommandSub):
        node = cast(command_sub, UP_node)

        id_ = node.left_token.id
        # &(echo block literal)
        if id_ == Id.Left_CaretParen:
          return 'TODO: value.Block'
        else:
          stdout = self.shell_ex.RunCommandSub(node)
          if id_ == Id.Left_AtParen:  # @(seq 3)
            strs = self.splitter.SplitForWordEval(stdout)
            return strs
          else:
            return stdout

      elif case(expr_e.ShArrayLiteral):
        node = cast(sh_array_literal, UP_node)

        words = braces.BraceExpandWords(node.words)
        strs = self.word_ev.EvalWordSequence(words)
        #log('ARRAY LITERAL EVALUATED TO -> %s', strs)
        # TODO: unify with value_t
        return objects.StrArray(strs)

      elif case(expr_e.DoubleQuoted):
        node = cast(double_quoted, UP_node)

        # In an ideal world, I would *statically* disallow:
        # - "$@" and "${array[@]}"
        # - backticks like `echo hi`  
        # - $(( 1+2 )) and $[] -- although useful for refactoring
        #   - not sure: ${x%%} -- could disallow this
        #     - these enters the ArgDQ state: "${a:-foo bar}" ?
        # But that would complicate the parser/evaluator.  So just rely on
        # strict_array to disallow the bad parts.
        return self.word_ev.EvalDoubleQuotedToString(node)

      elif case(expr_e.SingleQuoted):
        node = cast(single_quoted, UP_node)
        return word_compile.EvalSingleQuoted(node)

      elif case(expr_e.BracedVarSub):
        node = cast(braced_var_sub, UP_node)
        return self.word_ev.EvalBracedVarSubToString(node)

      elif case(expr_e.SimpleVarSub):
        node = cast(simple_var_sub, UP_node)
        return self.word_ev.EvalSimpleVarSubToString(node.token)

      elif case(expr_e.Unary):
        node = cast(expr__Unary, UP_node)

        child = self._EvalExpr(node.child)
        if node.op.id == Id.Arith_Minus:
          return -child
        if node.op.id == Id.Arith_Tilde:
          return ~child
        if node.op.id == Id.Expr_Not:
          return not child

        raise NotImplementedError(node.op.id)

      elif case(expr_e.Binary):
        node = cast(expr__Binary, UP_node)

        left = self._EvalExpr(node.left)
        right = self._EvalExpr(node.right)

        if node.op.id == Id.Arith_Plus:
          return left + right
        if node.op.id == Id.Arith_Minus:
          return left - right
        if node.op.id == Id.Arith_Star:
          return left * right
        if node.op.id == Id.Arith_Slash:
          # NOTE: does not depend on from __future__ import division
          try:
            result = float(left) / right  # floating point division
          except ZeroDivisionError:
            raise error.Expr('divide by zero', token=node.op)

          return result

        if node.op.id == Id.Expr_DSlash:
          return left // right  # integer divison
        if node.op.id == Id.Arith_Percent:
          return left % right

        if node.op.id == Id.Arith_DStar:  # Exponentiation
          return left ** right

        if node.op.id == Id.Arith_DPlus:
          # list or string concatenation
          return left + right

        # Bitwise
        if node.op.id == Id.Arith_Amp:
          return left & right
        if node.op.id == Id.Arith_Pipe:
          return left | right
        if node.op.id == Id.Arith_Caret:
          return left ^ right
        if node.op.id == Id.Arith_DGreat:
          return left >> right
        if node.op.id == Id.Arith_DLess:
          return left << right

        # Logical
        if node.op.id == Id.Expr_And:
          return left and right
        if node.op.id == Id.Expr_Or:
          return left or right

        raise NotImplementedError(node.op.id)

      elif case(expr_e.Range):  # 1:10  or  1:10:2
        node = cast(expr__Range, UP_node)

        lower = self._EvalExpr(node.lower)
        upper = self._EvalExpr(node.upper)
        return xrange(lower, upper)

      elif case(expr_e.Slice):  # a[:0]
        node = cast(expr__Slice, UP_node)

        lower = self._EvalExpr(node.lower) if node.lower else None
        upper = self._EvalExpr(node.upper) if node.upper else None
        return slice(lower, upper)

      elif case(expr_e.Compare):
        node = cast(expr__Compare, UP_node)

        left = self._EvalExpr(node.left)
        result = True  # Implicit and
        for op, right_expr in zip(node.ops, node.comparators):

          right = self._EvalExpr(right_expr)

          if op.id == Id.Arith_Less:
            result = left < right
          elif op.id == Id.Arith_Great:
            result = left > right
          elif op.id == Id.Arith_GreatEqual:
            result = left >= right
          elif op.id == Id.Arith_LessEqual:
            result = left <= right

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
              e_die('~== expects a string on the left', span_id=op.span_id)

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

            e_die('~== expects Str, Int, or Bool on the right',
                  span_id=op.span_id)

          else:
            try:
              if op.id == Id.Arith_Tilde:
                result = self._EvalMatch(left, right, True)

              elif op.id == Id.Expr_NotTilde:
                result = not self._EvalMatch(left, right, False)

              else:
                raise AssertionError(op.id)
            except RuntimeError as e:
              # Status 2 indicates a regex parse error.  This is fatal in OSH but
              # not in bash, which treats [[ like a command with an exit code.
              e_die_status(2, 'Invalid regex %r' % right, span_id=op.span_id)

          if not result:
            return result

          left = right
        return result
   
      elif case(expr_e.IfExp):
        node = cast(expr__IfExp, UP_node)

        b = self._EvalExpr(node.test)
        if b:
          return self._EvalExpr(node.body)
        else:
          return self._EvalExpr(node.orelse)

      elif case(expr_e.List):
        node = cast(expr__List, UP_node)
        return [self._EvalExpr(e) for e in node.elts]

      elif case(expr_e.Tuple):
        node = cast(expr__Tuple, UP_node)
        return tuple(self._EvalExpr(e) for e in node.elts)

      elif case(expr_e.Dict):
        node = cast(expr__Dict, UP_node)

        # NOTE: some keys are expr.Const
        keys = [self._EvalExpr(e) for e in node.keys]

        values = []
        for i, value_expr in enumerate(node.values):
          if value_expr.tag == expr_e.Implicit:
            v = self.LookupVar(keys[i])  # {name}
          else:
            v = self._EvalExpr(value_expr)
          values.append(v)

        d = NewDict()
        for k, v in zip(keys, values):
          d[k] = v
        return d

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
        iter_name = comp.lhs[0].name.val

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
              lvalue.Named(iter_name), value.Obj(loop_val), scope_e.LocalOnly)

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
        node = cast(expr__FuncCall, UP_node)

        func = self._EvalExpr(node.func)
        pos_args, named_args = self.EvalArgList(node.args)
        ret = func(*pos_args, **named_args)
        return ret

      elif case(expr_e.Subscript):
        node = cast(subscript, UP_node)

        obj = self._EvalExpr(node.obj)
        index = self._EvalIndices(node.indices)
        try:
          result = obj[index]
        except KeyError:
          # TODO: expr.Subscript has no error location
          raise error.Expr('dict entry not found', span_id=runtime.NO_SPID)
        except IndexError:
          # TODO: expr.Subscript has no error location
          raise error.Expr('index out of range', span_id=runtime.NO_SPID)

        return result

      # Note: This is only for the obj.method() case.  We will probably change
      # the AST and get rid of getattr().
      elif case(expr_e.Attribute):  # obj.attr 
        node = cast(attribute, UP_node)

        o = self._EvalExpr(node.obj)
        id_ = node.op.id
        if id_ == Id.Expr_Dot:
          # Used for .startswith()
          name = node.attr.val
          return getattr(o, name)

        if id_ == Id.Expr_RArrow:  # d->key is like d['key']
          name = node.attr.val
          try:
            result = o[name]
          except KeyError:
            raise error.Expr('dict entry not found', token=node.op)

          return result

        if id_ == Id.Expr_DColon:  # StaticName::member
          raise NotImplementedError(id_)

          # TODO: We should prevent virtual lookup here?  This is a pure static
          # namespace lookup?
          # But Python doesn't any hook for this.
          # Maybe we can just check that it's a module?  And modules don't lookup
          # in a supertype or __class__, etc.

        raise AssertionError(id_)

      elif case(expr_e.RegexLiteral):
        node = cast(expr__RegexLiteral, UP_node)

        # TODO: Should this just be an object that ~ calls?
        return objects.Regex(self.EvalRegex(node.regex))

      else:
        raise NotImplementedError(node.__class__.__name__)

  def _EvalClassLiteralTerm(self, term):
    # type: (class_literal_term_t) -> class_literal_term_t
    UP_term = term

    s = None  # type: str
    spid = runtime.NO_SPID

    with tagswitch(term) as case:
      if case(class_literal_term_e.SingleQuoted):
        term = cast(single_quoted, UP_term)

        s = word_compile.EvalSingleQuoted(term)
        spid = term.left.span_id

      elif case(class_literal_term_e.DoubleQuoted):
        term = cast(double_quoted, UP_term)

        s = self.word_ev.EvalDoubleQuotedToString(term)
        spid = term.left.span_id

      elif case(class_literal_term_e.BracedVarSub):
        term = cast(braced_var_sub, UP_term)

        s = self.word_ev.EvalBracedVarSubToString(term)
        spid = term.spids[0]

      elif case(class_literal_term_e.SimpleVarSub):
        term = cast(simple_var_sub, UP_term)

        s = self.word_ev.EvalSimpleVarSubToString(term.token)
        spid = term.token.span_id

      elif case(class_literal_term_e.CharLiteral):
        term = cast(class_literal_term__CharLiteral, UP_term)

        # What about \0?
        # At runtime, ERE should disallow it.  But we can also disallow it here.
        return word_compile.EvalCharLiteralForRegex(term.tok)

    if s is not None:
      # A string like '\x7f\xff' should be presented like
      if len(s) > 1:
        for c in s:
          if ord(c) > 128:
            e_die("Express these bytes as character literals to avoid "
                  "confusing them with encoded characters", span_id=spid)

      return class_literal_term.ByteSet(s, spid)
    else:
      return term

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
        node = cast(re__Seq, UP_node)
        new_children = [self._EvalRegex(child) for child in node.children]
        return re.Seq(new_children)

      elif case(re_e.Alt):
        node = cast(re__Alt, UP_node)
        new_children = [self._EvalRegex(child) for child in node.children]
        return re.Alt(new_children)

      elif case(re_e.Repeat):
        node = cast(re__Repeat, UP_node)
        return re.Repeat(self._EvalRegex(node.child), node.op)

      elif case(re_e.Group):
        node = cast(re__Group, UP_node)
        return re.Group(self._EvalRegex(node.child))

      elif case(re_e.Capture):  # Identical to Group
        node = cast(re__Capture, UP_node)
        return re.Capture(self._EvalRegex(node.child), node.var_name)

      elif case(re_e.ClassLiteral):
        node = cast(re__ClassLiteral, UP_node)

        new_terms = [self._EvalClassLiteralTerm(t) for t in node.terms]
        return re.ClassLiteral(node.negated, new_terms)

      elif case(re_e.Speck):
        node = cast(speck, UP_node)

        id_ = node.id
        if id_ == Id.Expr_Dot:
          return re.Primitive(Id.Re_Dot)
        elif id_ == Id.Arith_Caret:  # ^
          return re.Primitive(Id.Re_Start)
        elif id_ == Id.Expr_Dollar:  # $
          return re.Primitive(Id.Re_End)
        else:
          raise NotImplementedError(id_)

      elif case(re_e.Token):
        node = cast(Token, UP_node)

        id_ = node.id
        val = node.val

        if id_ == Id.Expr_Name:
          if val == 'dot':
            return re.Primitive(Id.Re_Dot)
          else:
            raise NotImplementedError(val)

        elif id_ == Id.Expr_Symbol:
          if val == '%start':
            return re.Primitive(Id.Re_Start)
          elif val == '%end':
            return re.Primitive(Id.Re_End)
          else:
            raise NotImplementedError(val)

        else:  # Must be Id.Char_{OneChar,Hex,Unicode4,Unicode8}
          kind = consts.GetKind(id_)
          assert kind == Kind.Char, id_
          s = word_compile.EvalCStringToken(node)
          return re.LiteralChars(s, node.span_id)

      elif case(re_e.SingleQuoted):
        node = cast(single_quoted, UP_node)

        s = word_compile.EvalSingleQuoted(node)
        return re.LiteralChars(s, node.left.span_id)

      elif case(re_e.DoubleQuoted):
        node = cast(double_quoted, UP_node)

        s = self.word_ev.EvalDoubleQuotedToString(node)
        return re.LiteralChars(s, node.left.span_id)

      elif case(re_e.BracedVarSub):
        node = cast(braced_var_sub, UP_node)

        s = self.word_ev.EvalBracedVarSubToString(node)
        return re.LiteralChars(s, node.spids[0])

      elif case(re_e.SimpleVarSub):
        node = cast(simple_var_sub, UP_node)

        s = self.word_ev.EvalSimpleVarSubToString(node.token)
        return re.LiteralChars(s, node.token.span_id)

      elif case(re_e.Splice):
        node = cast(re__Splice, UP_node)

        obj = self.LookupVar(node.name.val, span_id=node.name.span_id)
        if not isinstance(obj, objects.Regex):
          e_die("Can't splice object of type %r into regex", obj.__class__,
                token=node.name)
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


