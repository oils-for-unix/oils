#!/usr/bin/env python2
"""
expr_eval.py
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import (
    expr_e, expr_t, word_part_e
)
from _devbuild.gen.runtime_asdl import (
    lvalue, value_e, scope_e,
)
from core.util import e_die
#from core.util import log
from oil_lang import objects
from osh import braces

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

  def EvalWordPart(self, part):
    """
    TODO: We might not want oil_word_part_e?  Just use OSH word_part?
    """
    if part.tag == word_part_e.Literal:
      return part.token.val

    raise NotImplementedError(part.__class__.__name__)

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
      return int(node.c.val)

    if node.tag == expr_e.Var:
      return self.LookupVar(node.name.val)

    if node.tag == expr_e.CommandSub:
      return self.ex.RunCommandSub(node.command_list)

    if node.tag == expr_e.ShellArrayLiteral:
      words = node.items
      words = braces.BraceExpandWords(words)
      strs = self.word_ev.EvalWordSequence(words)
      #log('ARRAY LITERAL EVALUATED TO -> %s', strs)
      return objects.StrArray(strs)

    if node.tag == expr_e.DoubleQuoted:
      s = ''.join(self.EvalWordPart(part) for part in node.parts)
      return s

    if node.tag == expr_e.Unary:
      child = self.EvalExpr(node.child)
      if node.op.id == Id.Arith_Minus:
        return -child

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

      if node.op.id == Id.Arith_Less:
        return left < right

      if node.op.id == Id.Arith_Great:
        return left > right

      raise NotImplementedError(node.op.id)

    if node.tag == expr_e.List:
      return [self.EvalExpr(e) for e in node.elts]

    if node.tag == expr_e.FuncCall:
      # TODO:
      # First cut builtins:
      #
      # len() Int
      # split(s Str) StrArray (what about List[Str])?
      # join(s StrArray) Str
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

    raise NotImplementedError(node.__class__.__name__)
