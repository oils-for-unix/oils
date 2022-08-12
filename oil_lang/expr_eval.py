#!/usr/bin/env python2
"""
expr_eval.py
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Kind
from _devbuild.gen.syntax_asdl import (
    expr_e, expr_t, re, re_e, re_t, class_literal_term, class_literal_term_e,
    place_expr_e, place_expr_t,
)
from _devbuild.gen.runtime_asdl import (
    lvalue, value, value_e, scope_e,
)
from asdl import runtime
from core import error
from core import state
from core.pyerror import e_die, e_die_status, log
from frontend import consts
from oil_lang import objects
from osh import braces
from osh import word_compile
from mycpp.mylib import NewDict

import libc

from typing import Any, Dict, Optional, List, Union, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import (
      lvalue_t, lvalue__Named, lvalue__ObjIndex, lvalue__ObjAttr,
  )
  from _devbuild.gen.syntax_asdl import arg_list
  from core.vm import _Executor
  from core.ui import ErrorFormatter
  from core.state import Mem
  from osh.word_eval import StringWordEvaluator
  from osh import split

_ = log


def LookupVar(mem, var_name, which_scopes, span_id=runtime.NO_SPID):
  """Convert to a Python object so we can calculate on it natively."""

  # Lookup WITHOUT dynamic scope.
  val = mem.GetValue(var_name, which_scopes=which_scopes)
  if val.tag == value_e.Undef:
    # TODO: Location info
    e_die('Undefined variable %r', var_name, span_id=span_id)

  if val.tag == value_e.Str:
    return val.s
  if val.tag == value_e.MaybeStrArray:
    return val.strs  # node: has None
  if val.tag == value_e.AssocArray:
    return val.d
  if val.tag == value_e.Obj:
    return val.obj


class OilEvaluator(object):
  """Shared between arith and bool evaluators.

  They both:

  1. Convert strings to integers, respecting shopt -s strict_arith.
  2. Look up variables and evaluate words.
  """

  def __init__(self,
               mem,  # type: Mem
               mutable_opts,  # type: state.MutableOpts
               funcs,  # type: Dict
               splitter,  # type: split.SplitContext
               errfmt,  # type: ErrorFormatter
               ):
    # type: (...) -> None
    self.shell_ex = None  # type: _Executor
    self.word_ev = None  # type: StringWordEvaluator

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
    # type: (lvalue_t, Union[int, float]) -> Union[int, float]
    lhs_py = self.LookupVar(lval.name)
    if not isinstance(lhs_py, (int, float)):
      # TODO: Could point at the variable name
      e_die("Object of type %r doesn't support +=", lhs_py.__class__.__name__)

    return lhs_py + rhs_py

  def EvalLHS(self, node):
    if 0:
      print('EvalLHS()')
      node.PrettyPrint()
      print('')

    if node.tag == expr_e.Var:
      return lvalue.Named(node.name.val)
    else:
      # TODO:
      # subscripts, tuple unpacking, starred expressions, etc.

      raise NotImplementedError(node.__class__.__name__)

  # Copied from BoolEvaluator
  def _EvalMatch(self, left, right, set_match_result):
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
    # type: (arg_list) -> Tuple[List[Any], Dict[str, Any]]
    """ Used by do f(x) and echo $f(x). """
    pos_args = []
    for arg in args.positional:
      if arg.tag == expr_e.Spread:
        # assume it returns a list
        pos_args.extend(self.EvalExpr(arg.child))
      else:
        pos_args.append(self.EvalExpr(arg))

    kwargs = {}
    for arg in args.named:
      if arg.name:
        kwargs[arg.name.val] = self.EvalExpr(arg.value)
      else:
        # ...named
        kwargs.update(self.EvalExpr(arg.value))
    return pos_args, kwargs

  def _EvalIndices(self, indices):
    if len(indices) == 1:
      return self.EvalExpr(indices[0])
    else:
      # e.g. mydict[a,b]
      return tuple(self.EvalExpr(ind) for ind in indices)

  def EvalPlaceExpr(self, place):
    # type: (place_expr_t) -> Union[lvalue__Named, lvalue__ObjIndex, lvalue__ObjAttr]
    if place.tag == place_expr_e.Var:
      return lvalue.Named(place.name.val)

    if place.tag == place_expr_e.Subscript:
      obj = self.EvalExpr(place.obj)
      index = self._EvalIndices(place.indices)
      return lvalue.ObjIndex(obj, index)

    if place.tag == place_expr_e.Attribute:
      obj = self.EvalExpr(place.obj)
      if place.op.id == Id.Expr_RArrow:
        index = place.attr.val
        return lvalue.ObjIndex(obj, index)
      else:
        return lvalue.ObjAttr(obj, place.attr.val)

    raise NotImplementedError(place)

  def EvalExpr(self, node):
    # type: (expr_t) -> Any
    """Public API for _EvalExpr that ensures that command_sub_errexit is on."""
    try:
      with state.ctx_OilExpr(self.mutable_opts):
        return self._EvalExpr(node)
    except TypeError as e:
      # TODO: Add location info.  Right now we blame the variable name for
      # 'var' and 'setvar', etc.
      raise error.Expr('Type error in expression: %s' % str(e))
    except (AttributeError, ValueError) as e:
      raise error.Expr('Expression eval error: %s' % str(e))

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

    if node.tag == expr_e.Const:
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

    if node.tag == expr_e.Var:
      return self.LookupVar(node.name.val, span_id=node.name.span_id)

    if node.tag == expr_e.CommandSub:
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

    if node.tag == expr_e.ShArrayLiteral:
      words = braces.BraceExpandWords(node.words)
      strs = self.word_ev.EvalWordSequence(words)
      #log('ARRAY LITERAL EVALUATED TO -> %s', strs)
      # TODO: unify with value_t
      return objects.StrArray(strs)

    if node.tag == expr_e.DoubleQuoted:
      # In an ideal world, I would *statically* disallow:
      # - "$@" and "${array[@]}"
      # - backticks like `echo hi`  
      # - $(( 1+2 )) and $[] -- although useful for refactoring
      #   - not sure: ${x%%} -- could disallow this
      #     - these enters the ArgDQ state: "${a:-foo bar}" ?
      # But that would complicate the parser/evaluator.  So just rely on
      # strict_array to disallow the bad parts.
      return self.word_ev.EvalDoubleQuotedToString(node)

    if node.tag == expr_e.SingleQuoted:
      return word_compile.EvalSingleQuoted(node)

    if node.tag == expr_e.BracedVarSub:
      return self.word_ev.EvalBracedVarSubToString(node)

    if node.tag == expr_e.SimpleVarSub:
      return self.word_ev.EvalSimpleVarSubToString(node.token)

    if node.tag == expr_e.Unary:
      child = self._EvalExpr(node.child)
      if node.op.id == Id.Arith_Minus:
        return -child
      if node.op.id == Id.Arith_Tilde:
        return ~child
      if node.op.id == Id.Expr_Not:
        return not child

      raise NotImplementedError(node.op.id)

    if node.tag == expr_e.Binary:
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

    if node.tag == expr_e.Range:  # 1:10  or  1:10:2
      lower = self._EvalExpr(node.lower)
      upper = self._EvalExpr(node.upper)
      return xrange(lower, upper)

    if node.tag == expr_e.Slice:  # a[:0]
      lower = self._EvalExpr(node.lower) if node.lower else None
      upper = self._EvalExpr(node.upper) if node.upper else None
      return slice(lower, upper)

    if node.tag == expr_e.Compare:
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
 
    if node.tag == expr_e.IfExp:
      b = self._EvalExpr(node.test)
      if b:
        return self._EvalExpr(node.body)
      else:
        return self._EvalExpr(node.orelse)

    if node.tag == expr_e.List:
      return [self._EvalExpr(e) for e in node.elts]

    if node.tag == expr_e.Tuple:
      return tuple(self._EvalExpr(e) for e in node.elts)

    if node.tag == expr_e.Dict:
      # NOTE: some keys are expr.Const
      keys = [self._EvalExpr(e) for e in node.keys]

      values = []
      for i, e in enumerate(node.values):
        if e.tag == expr_e.Implicit:
          v = self.LookupVar(keys[i])  # {name}
        else:
          v = self._EvalExpr(e)
        values.append(v)

      d = NewDict()
      for k, v in zip(keys, values):
        d[k] = v
      return d

    if node.tag == expr_e.ListComp:
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

    if node.tag == expr_e.GeneratorExp:
      e_die_status(2, 'Generator expression reserved but not implemented')

    if node.tag == expr_e.Lambda:  # |x| x+1 syntax is reserved
      # TODO: Location information for |, or func
      # Note: anonymous functions also evaluate to a Lambda, but they shouldn't
      e_die_status(2, 'Lambda reserved but not implemented')

    if node.tag == expr_e.FuncCall:
      func = self._EvalExpr(node.func)
      pos_args, named_args = self.EvalArgList(node.args)
      ret = func(*pos_args, **named_args)
      return ret

    if node.tag == expr_e.Subscript:
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
    if node.tag == expr_e.Attribute:  # obj.attr 
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

    if node.tag == expr_e.RegexLiteral:
      # TODO: Should this just be an object that ~ calls?
      return objects.Regex(self.EvalRegex(node.regex))

    raise NotImplementedError(node.__class__.__name__)

  def _EvalClassLiteralPart(self, part):
    # TODO: You can RESOLVE strings -> literal
    # Technically you can also @ if it contains exactly ONE CharClassLiteral?
    # But leave it out for now.
    return part

  def _MaybeReplaceLeaf(self, node):
    # type: (re_t) -> Tuple[Optional[re_t], bool]
    """
    If a leaf node needs to be evaluated, do it and return the replacement.
    Otherwise return None.
    """
    new_leaf = None
    recurse = True

    if node.tag == re_e.Speck:
      id_ = node.id
      if id_ == Id.Expr_Dot:
        new_leaf = re.Primitive(Id.Re_Dot)
      elif id_ == Id.Arith_Caret:  # ^
        new_leaf = re.Primitive(Id.Re_Start)
      elif id_ == Id.Expr_Dollar:  # $
        new_leaf = re.Primitive(Id.Re_End)
      else:
        raise NotImplementedError(id_)

    elif node.tag == re_e.Token:
      id_ = node.id
      val = node.val

      if id_ == Id.Expr_Name:
        if val == 'dot':
          new_leaf = re.Primitive(Id.Re_Dot)
        else:
          raise NotImplementedError(val)

      elif id_ == Id.Expr_Symbol:
        if val == '%start':
          new_leaf = re.Primitive(Id.Re_Start)
        elif val == '%end':
          new_leaf = re.Primitive(Id.Re_End)
        else:
          raise NotImplementedError(val)

      else:  # Must be Id.Char_{OneChar,Hex,Unicode4,Unicode8}
        kind = consts.GetKind(id_)
        assert kind == Kind.Char, id_
        s = word_compile.EvalCStringToken(node)
        new_leaf = re.LiteralChars(s, node.span_id)

    elif node.tag == re_e.SingleQuoted:
      s = word_compile.EvalSingleQuoted(node)
      new_leaf = re.LiteralChars(s, node.left.span_id)

    elif node.tag == re_e.DoubleQuoted:
      s = self.word_ev.EvalDoubleQuotedToString(node)
      new_leaf = re.LiteralChars(s, node.left.span_id)

    elif node.tag == re_e.BracedVarSub:
      s = self.word_ev.EvalBracedVarSubToString(node)
      new_leaf = re.LiteralChars(s, node.spids[0])

    elif node.tag == re_e.SimpleVarSub:
      s = self.word_ev.EvalSimpleVarSubToString(node.token)
      new_leaf = re.LiteralChars(s, node.token.span_id)

    elif node.tag == re_e.Splice:
      obj = self.LookupVar(node.name.val, span_id=node.name.span_id)
      if not isinstance(obj, objects.Regex):
        e_die("Can't splice object of type %r into regex", obj.__class__,
              token=node.name)
      # Note: we only splice the regex, and ignore flags.
      # Should we warn about this?
      new_leaf = obj.regex

    # These are leaves we don't need to do anything with.
    elif node.tag == re_e.PosixClass:
      recurse = False
    elif node.tag == re_e.PerlClass:
      recurse = False

    return new_leaf, recurse

  def _MutateChildren(self, children):
    # type: (List[re_t]) -> None
    """
    """
    for i, c in enumerate(children):
      new_leaf, recurse = self._MaybeReplaceLeaf(c)
      if new_leaf:
        children[i] = new_leaf
      elif recurse:
        self._MutateSubtree(c)

  def _MutateClassLiteral(self, node):
    # type: (re_t) -> None
    for i, term in enumerate(node.terms):
      s = None
      if term.tag == class_literal_term_e.SingleQuoted:
        s = word_compile.EvalSingleQuoted(term)
        spid = term.left.span_id

      elif term.tag == class_literal_term_e.DoubleQuoted:
        s = self.word_ev.EvalDoubleQuotedToString(term)
        spid = term.left.span_id

      elif term.tag == class_literal_term_e.BracedVarSub:
        s = self.word_ev.EvalBracedVarSubToString(term)
        spid = term.spids[0]

      elif term.tag == class_literal_term_e.SimpleVarSub:
        s = self.word_ev.EvalSimpleVarSubToString(term.token)
        spid = term.token.span_id

      elif term.tag == class_literal_term_e.CharLiteral:
        # What about \0?
        # At runtime, ERE should disallow it.  But we can also disallow it here.
        new_leaf = word_compile.EvalCharLiteralForRegex(term.tok)
        if new_leaf:
          node.terms[i] = new_leaf

      if s is not None:
        # A string like '\x7f\xff' should be presented like
        if len(s) > 1:
          for c in s:
            if ord(c) > 128:
              e_die("Express these bytes as character literals to avoid "
                    "confusing them with encoded characters", span_id=spid)

        node.terms[i] = class_literal_term.ByteSet(s, spid)

  def _MutateSubtree(self, node):
    if node.tag == re_e.Seq:
      self._MutateChildren(node.children)
      return

    if node.tag == re_e.Alt:
      self._MutateChildren(node.children)
      return

    if node.tag == re_e.Repeat:
      new_leaf, recurse = self._MaybeReplaceLeaf(node.child)
      if new_leaf:
        node.child = new_leaf
      elif recurse:
        self._MutateSubtree(node.child)
      return

    # TODO: How to consolidate this code with the above?
    if node.tag in (re_e.Group, re_e.Capture):
      new_leaf, recurse = self._MaybeReplaceLeaf(node.child)
      if new_leaf:
        node.child = new_leaf
      elif recurse:
        self._MutateSubtree(node.child)
      return

    if node.tag == re_e.ClassLiteral:
      self._MutateClassLiteral(node)
      return

  def EvalRegex(self, node):
    # type: (re_t) -> re_t
    """
    Resolve the references in an eggex, e.g. Hex and $const in
    
    / Hex '.' $const "--$const" /
    """
    # An evaluated Regex shares the same structure as the AST, but uses
    # slightly different nodes.
    #
    # * Speck/Token (syntactic concepts) -> Primitive (logical)
    # * Splice -> Resolved
    # * All Strings -> Literal
    #
    # Note: there have been BUGS as a result of running this in a loop (see
    # spec/oil-regex).  Should we have two different node types?  This is an
    # "AST typing" problem.

    new_leaf, recurse = self._MaybeReplaceLeaf(node)
    if new_leaf:
      return new_leaf
    elif recurse:
      self._MutateSubtree(node)

    # View it after evaluation
    if 0:
      log('After evaluation:')
      node.PrettyPrint(); print()
    return node
