#!/usr/bin/env python2
"""
expr_eval.py
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Kind
from _devbuild.gen.syntax_asdl import (
    expr_e, expr_t, re, re_e, re_t, class_literal_term, class_literal_term_e,
    command,
)
from _devbuild.gen.runtime_asdl import (
    lvalue, value, value_e, scope_e,
)
from core import meta
from core.util import e_die
from core.util import log
from oil_lang import objects
from osh import braces
from osh import state
from osh import word_compile
from osh import word_eval

import libc

from typing import Any, Optional, List

_ = log


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
    # TODO: Rename EggEx?
    if isinstance(right, str):
      pass
    elif isinstance(right, objects.Regex):
      right = right.AsPosixEre()
    else:
      raise RuntimeError(
          "RHS of ~ should be string or Regex (got %s)" % right.__class__.__name__)
    
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

      # NOTE: We could allow Ellipsis for a[:, ...] here, but we're not using
      # it yet.
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
      return word_eval.EvalSingleQuoted(node)

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

      raise NotImplementedError(node.op.id)

    if node.tag == expr_e.Range:  # 1:10  or  1:10:2
      lower = self.EvalExpr(node.lower)
      upper = self.EvalExpr(node.upper)
      return xrange(lower, upper)

    if node.tag == expr_e.Slice:  # a[:0]
      lower = self.EvalExpr(node.lower) if node.lower else None
      upper = self.EvalExpr(node.upper) if node.upper else None
      return slice(lower, upper)

    if node.tag == expr_e.Compare:
      left = self.EvalExpr(node.left)
      result = True  # Implicit and
      for op, right_expr in zip(node.ops, node.comparators):

        right = self.EvalExpr(right_expr)

        if op.id == Id.Arith_Less:
          result = left < right
        elif op.id == Id.Arith_Great:
          result = left > right
        elif op.id == Id.Arith_GreatEqual:
          result = left >= right
        elif op.id == Id.Arith_LessEqual:
          result = left <= right
        elif op.id == Id.Arith_DEqual:
          result = left == right

        elif op.id == Id.Expr_In:
          result = left in right
        elif op.id == Id.Node_NotIn:
          result = left not in right

        elif op.id == Id.Expr_Is:
          result = left is right
        elif op.id == Id.Node_IsNot:
          result = left is not right

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
            e_die("Invalid regex %r", right, span_id=op.span_id, status=2)

        if not result:
          return result

        left = right
      return result
 
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
      iter_name = comp.lhs[0].name.val

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

    if node.tag == expr_e.GeneratorExp:
      comp = node.generators[0]
      obj = self.EvalExpr(comp.iter)

      # TODO: Support (x for x, y in ...)
      iter_name = comp.lhs[0].name.val

      it = iter(obj)

      # TODO: There is probably a much better way to do this!
      #       The scope of the loop variable is wrong, etc.

      def _gen():
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
            yield item

      return _gen()

    if node.tag == expr_e.Lambda:
      return objects.Lambda(node, self.ex)

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

      # TODO: Need to match up named args here

      args = [self.EvalExpr(a) for a in node.args]
      kwargs = []

      ret = func(*args)
      return ret

    if node.tag == expr_e.Subscript:
      collection = self.EvalExpr(node.collection)

      if len(node.indices) == 1:
        index = self.EvalExpr(node.indices[0])
      else:
        # e.g. mydict[a,b]
        index = tuple(self.EvalExpr(ind) for ind in node.indices)

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

    if node.tag == expr_e.RegexLiteral:  # obj.attr 
      # TODO: Should this just be an object that ~ calls?
      return objects.Regex(self.EvalRegex(node.regex))

    if node.tag == expr_e.ArrayLiteral:  # obj.attr 
      items = [self.EvalExpr(item) for item in node.items]
      if items:
        # Determine type at runtime?  If we have something like @[(i) (j)]
        # then we don't know its type until runtime.

        first = items[0]
        if isinstance(first, bool):
          return objects.BoolArray(bool(x) for x in items)
        elif isinstance(first, int):
          return objects.IntArray(int(x) for x in items)
        elif isinstance(first, float):
          return objects.FloatArray(float(x) for x in items)
        elif isinstance(first, str):
          return objects.StrArray(str(x) for x in items)
        else:
          raise AssertionError(first)
      else:
        # TODO: Should this have an unknown type?
        # What happens when you mutate or extend it?  You have to make sure
        # that the type tags match?
        return objects.BoolArray(items)

    raise NotImplementedError(node.__class__.__name__)

  def _EvalClassLiteralPart(self, part):
    # TODO: You can RESOLVE strings -> literal
    # Technically you can also @ if it contains exactly ONE CharClassLiteral?
    # But leave it out for now.

    return part

    raise NotImplementedError(part.__class__.__name__)

  def _MaybeReplaceLeaf(self, node):
    # type: (re_t) -> Optional[re_t]
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
        kind = meta.LookupKind(id_)
        assert kind == Kind.Char, id_
        s = word_compile.EvalCStringToken(id_, val)
        new_leaf = re.LiteralChars(s, node.span_id)

    elif node.tag == re_e.SingleQuoted:
      s = word_eval.EvalSingleQuoted(node)
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
      obj = self.LookupVar(node.name.val)
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
        s = word_eval.EvalSingleQuoted(term)
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
        node.terms[i] = word_compile.EvalCharLiteralForRegex(term.tok)

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
    if node.tag == re_e.Group:
      new_leaf, recurse = self._MaybeReplaceLeaf(node.child)
      if new_leaf:
        node.child = new_leaf
      elif recurse:
        self._MutateSubtree(node.child)
      return

    elif node.tag == re_e.ClassLiteral:
      self._MutateClassLiteral(node)
      return

    raise NotImplementedError(node.__class__.__name__)

  def EvalRegex(self, node):
    # type: (re_t) -> re_t
    
    # Regex Evaluation Shares the Same Structure, but uses slightly different
    # nodes.
    # * Speck/Token (syntactic concepts) -> Primitive (logical)
    # * Splice -> Resolved
    # * All Strings -> Literal

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
