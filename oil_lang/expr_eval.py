#!/usr/bin/env python2
"""
expr_eval.py
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import (
    expr_e, expr_t,
)
from _devbuild.gen.runtime_asdl import (
    lvalue, value, value_e, scope_e,
)
from core.util import e_die
#from core.util import log
from oil_lang import objects
from osh import braces
from osh import state

import libc

from typing import Any


class OilEvaluator(object):
  """Shared between arith and bool evaluators.

  They both:

  1. Convert strings to integers, respecting shopt -s strict_arith.
  2. Look up variables and evaluate words.
  """

  def __init__(self, mem, funcs, ex, word_ev, errfmt):
    self.mem = mem
    self.funcs = funcs
    self.ex = ex
    self.word_ev = word_ev
    self.errfmt = errfmt

  def LookupVar(self, var_name):
    """Convert to a Python object so we can calculate on it natively."""

    # Lookup WITHOUT dynamic scope.
    val = self.mem.GetVar(var_name, lookup_mode=scope_e.LocalOnly)
    if val.tag == value_e.Undef:
      val = self.mem.GetVar(var_name, lookup_mode=scope_e.GlobalOnly)
      if val.tag == value_e.Undef:
        # TODO: Location info
        e_die('Undefined variable %r', var_name)

    if val.tag == value_e.Str:
      return val.s
    if val.tag == value_e.MaybeStrArray:
      return val.strs  # node: has None
    if val.tag == value_e.AssocArray:
      return val.d
    if val.tag == value_e.Obj:
      return val.obj

  def EvalPlusEquals(self, lval, rhs_py):
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
    matches = libc.regex_match(right, left)
    if matches:
      # TODO:
      # - Also set NAMED CAPTURES.
      #   - Idea: Set an OBJECT:
      #     M.group(0)   M.match()
      #     M.group(1)   M.group('foo')
      #     M.group(2)   M.group('bar')
      #
      #     Since it's statically parsed, it could be statically typed?
      #     $/ (digit+ as foo Int) /
      #
      #     Can use Python's __getattr__ and __index__ under the hood
      #     M[0]         M._ or M.match
      #     M[1]         M.foo
      #     M[2]         M.bar
      #
      # - Is 'M' the right name?  What do Perl and Ruby do?
      #   - BASH_REMATCH?
      if set_match_result:
        state.SetLocalArray(self.mem, 'M', matches)
      return True
    else:
      if set_match_result:
        # TODO: Clearing this would save allocations
        # NOTE: M does not exist initially.
        state.SetLocalArray(self.mem, 'M', [])
      return False

  def EvalExpr(self, node):
    # type: (expr_t) -> Any
    """
    This is a naive PyObject evaluator!  It uses the type dispatch of the host
    Python interpreter.

    Returns:
      A Python object of ANY type.  Should be wrapped in value.Obj() for
      storing in Mem.
    """
    if 0:
      print('EvalExpr()')
      node.PrettyPrint()
      print('')

    if node.tag == expr_e.Const:
      id_ = node.c.id

      if id_ == Id.Expr_DecInt:
        return int(node.c.val)
      elif id_ == Id.Expr_BinInt:
        return int(node.c.val, 2)
      elif id_ == Id.Expr_OctInt:
        return int(node.c.val, 8)
      elif id_ == Id.Expr_HexInt:
        return int(node.c.val, 16)

      elif id_ == Id.Expr_Float:
        return float(node.c.val)

      elif id_ == Id.Expr_Null:
        return None
      elif id_ == Id.Expr_True:
        return True
      elif id_ == Id.Expr_False:
        return False

      elif id_ == Id.Expr_Name:
        # for {name: 'bob'}
        # Maybe also :Symbol?
        return node.c.val

      raise AssertionError(id_)

    if node.tag == expr_e.Var:
      return self.LookupVar(node.name.val)

    if node.tag == expr_e.CommandSub:
      return self.ex.RunCommandSub(node.command_list)

    if node.tag == expr_e.ShArrayLiteral:
      words = braces.BraceExpandWords(node.words)
      strs = self.word_ev.EvalWordSequence(words)
      #log('ARRAY LITERAL EVALUATED TO -> %s', strs)
      return objects.StrArray(strs)

    if node.tag == expr_e.DoubleQuoted:
      # TODO: Disallow "$@" and "${array[@]}"
      # No part_value.Array
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
      return self.word_ev.EvalSingleQuoted(node)

    if node.tag == expr_e.BracedVarSub:
      return self.word_ev.EvalBracedVarSubToString(node)

    if node.tag == expr_e.SimpleVarSub:
      return self.word_ev.EvalSimpleVarSubToString(node.token)

    if node.tag == expr_e.Unary:
      child = self.EvalExpr(node.child)
      if node.op.id == Id.Arith_Minus:
        return -child
      if node.op.id == Id.Arith_Tilde:
        return ~child
      if node.op.id == Id.Expr_Not:
        return not child

      raise NotImplementedError(node.op.id)

    if node.tag == expr_e.Binary:
      left = self.EvalExpr(node.left)
      right = self.EvalExpr(node.right)

      if node.op.id == Id.Arith_Plus:
        return left + right
      if node.op.id == Id.Arith_Minus:
        return left - right
      if node.op.id == Id.Arith_Star:
        return left * right
      if node.op.id == Id.Arith_Slash:
        # NOTE: from __future__ import division changes 5/2!
        # But just make it explicit.
        return float(left) / right  # floating point division

      if node.op.id == Id.Expr_Div:
        return left // right  # integer divison
      if node.op.id == Id.Arith_Percent:
        return left % right

      if node.op.id == Id.Arith_Caret:  # Exponentiation
        return left ** right

      # Copmarison
      if node.op.id == Id.Arith_Less:
        return left < right
      if node.op.id == Id.Arith_Great:
        return left > right
      if node.op.id == Id.Arith_GreatEqual:
        return left >= right
      if node.op.id == Id.Arith_LessEqual:
        return left <= right
      if node.op.id == Id.Arith_DEqual:
        return left == right

      # Bitwise
      if node.op.id == Id.Arith_Amp:
        return left & right
      if node.op.id == Id.Arith_Pipe:
        return left | right
      if node.op.id == Id.Expr_Xor:
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

      try:
        if node.op.id == Id.Arith_Tilde:
          return self._EvalMatch(left, right, True)

        if node.op.id == Id.Expr_NotTilde:
          return not self._EvalMatch(left, right, False)
      except RuntimeError:
        # Status 2 indicates a regex parse error.  This is fatal in OSH but
        # not in bash, which treats [[ like a command with an exit code.
        e_die("Invalid regex %r", right, word=node.right, status=2)

      raise NotImplementedError(node.op.id)

    if node.tag == expr_e.IfExp:
      b = self.EvalExpr(node.test)
      if b:
        return self.EvalExpr(node.body)
      else:
        return self.EvalExpr(node.orelse)

    if node.tag == expr_e.List:
      return [self.EvalExpr(e) for e in node.elts]

    if node.tag == expr_e.Tuple:
      return tuple(self.EvalExpr(e) for e in node.elts)

    if node.tag == expr_e.Dict:
      # NOTE: some keys are expr.Const
      keys = [self.EvalExpr(e) for e in node.keys]

      values = []
      for i, e in enumerate(node.values):
        if e.tag == expr_e.Implicit:
          v = self.LookupVar(keys[i])  # {name}
        else:
          v = self.EvalExpr(e)
        values.append(v)

      return dict(zip(keys, values))

    if node.tag == expr_e.ListComp:

      # TODO:
      # - Consolidate with command_e.OilForIn in osh/cmd_exec.py?
      # - Do I have to push a temp frame here?
      #   Hm... lexical or dynamic scope is an issue.
      result = []
      comp = node.generators[0]
      obj = self.EvalExpr(comp.iter)

      # TODO: Handle x,y etc.
      iter_name = comp.target.name.val

      if isinstance(obj, str):
        e_die("Strings aren't iterable")
      else:
        it = iter(obj)

      while True:
        try:
          loop_val = next(it)  # e.g. x
        except StopIteration:
          break
        self.mem.SetVar(
            lvalue.Named(iter_name), value.Obj(loop_val), (),
            scope_e.LocalOnly)

        if comp.ifs:
          b = self.EvalExpr(comp.ifs[0])
        else:
          b = True

        if b:
          item = self.EvalExpr(node.elt)  # e.g. x*2
          result.append(item)

      return result

    if node.tag == expr_e.FuncCall:
      # TODO:
      #
      # Let Python handle type errors for now?

      # TODO: Lookup in equivalent of __builtins__
      #
      # shopt -s namespaces
      # 
      # builtin log "hello"
      # builtin log "hello"

      #node.PrettyPrint()

      # TODO: All functions called like f(x, y) must be in 'mem'.
      # Only 'procs' are in self.funcs

      # First look up the name in 'funcs'.  And then look it up
      # in 'mem' for first-class functions?
      #if node.func.tag == expr_e.Var:
      #  func = self.funcs.get(node.func.name.val)

      func = self.EvalExpr(node.func)

      args = [self.EvalExpr(a) for a in node.args]

      ret = func(*args)
      return ret

    if node.tag == expr_e.Subscript:
      collection = self.EvalExpr(node.collection)

      # TODO: handle multiple indices like a[i, j]
      index = self.EvalExpr(node.indices[0])
      return collection[index]

    # TODO: obj.method() should be separate
    if node.tag == expr_e.Attribute:  # obj.attr 
      o = self.EvalExpr(node.value)
      id_ = node.op.id
      if id_ == Id.Expr_Dot:
        name = node.attr.val
        # TODO: Does this do the bound method thing we do NOT want?
        return getattr(o, name)

      if id_ == Id.Expr_RArrow:  # d->key is like d['key']
        name = node.attr.val
        return o[name]

      if id_ == Id.Expr_DColon:  # StaticName::member
        raise NotImplementedError(id_)

        # TODO: We should prevent virtual lookup here?  This is a pure static
        # namespace lookup?
        # But Python doesn't any hook for this.
        # Maybe we can just check that it's a module?  And modules don't lookup
        # in a supertype or __class__, etc.

      raise AssertionError(id_)

    raise NotImplementedError(node.__class__.__name__)
