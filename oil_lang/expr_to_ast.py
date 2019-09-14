"""
expr_to_ast.py
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import (
    token, command, command__VarDecl,
    expr, expr_t, expr__DoubleQuoted, expr__SingleQuoted, expr__Dict,
    expr_context_e, regex, regex_t, word,
    word_t,
    word_part, word_part__CommandSub,
    param, type_expr_t,
    comprehension,
)
from _devbuild.gen import grammar_nt
from pgen2.parse import PNode
#from core.util import log

from typing import TYPE_CHECKING, List, Tuple, Optional, cast
if TYPE_CHECKING:
  from pgen2.grammar import Grammar


# Copied from pgen2/token.py to avoid dependency.
NT_OFFSET = 256

def ISNONTERMINAL(x):
    # type: (int) -> bool
    return x >= NT_OFFSET


class Transformer(object):
  """Homogeneous parse tree -> heterogeneous AST ("lossless syntax tree")

  pgen2 (Python's LL parser generator) doesn't have semantic actions like yacc,
  so this "transformer" is the equivalent.

  Files to refer to when modifying this function:

    oil_lang/grammar.pgen2 (generates _devbuild/gen/grammar_nt.py)
    frontend/syntax.asdl   (generates _devbuild/gen/syntax_asdl.py)

  Related examples:

    opy/compiler2/transformer.py (Python's parse tree -> AST, ~1500 lines)
    Python-2.7.13/Python/ast.c   (the "real" CPython version, ~3600 lines)

  Other:
    frontend/parse_lib.py  (turn on print_parse_tree)

  Public methods:
    Expr, VarDecl
    atom, trailer, etc. are private, named after productions in grammar.pgen2.
  """
  def __init__(self, gr):
    # type: (Grammar) -> None
    self.number2symbol = gr.number2symbol

  def _AssocBinary(self, children):
    # type: (List[PNode]) -> expr_t
    """For an associative binary operation.

    We don't care if it's (1+2)+3 or 1+(2+3).
    """
    if len(children) == 1:
      return self.Expr(children[0])

    # Note: Compare the iteractive com_binary() method in
    # opy/compiler2/transformer.py.

    left, op = children[0], children[1]
    if len(children) == 3:
      right = self.Expr(children[2])
    else:
      right = self._AssocBinary(children[2:])

    assert isinstance(op.tok, token)
    return expr.Binary(op.tok, self.Expr(left), right)

  def _Trailer(self, base, p_trailer):
    # type: (expr_t, PNode) -> expr_t
    children = p_trailer.children
    op_tok = children[0].tok

    # TODO: Need to process ALL the trailers, e.g. f(x, y)[1, 2](x, y)

    if op_tok.id == Id.Op_LParen:
      args = []  # type: List[expr_t]
      if len(children) == 2:  # ()
        return expr.FuncCall(base, args)

      p = children[1]  # the X in ( X )
      assert p.typ == grammar_nt.arglist  # f(x, y)
      self._Arglist(p.children, args)
      return expr.FuncCall(base, args)

    if op_tok.id == Id.Op_LBracket:
      p_args = children[1]

      if p_args.typ == grammar_nt.subscriptlist:
        # a, b, c -- every other one is a comma
        arglist = p_args.children[::2]
      else:
        arglist = [p_args]
      return expr.Subscript(base, [self.Expr(a) for a in arglist])

    if op_tok.id == Id.Expr_Dot:
      #return self._GetAttr(base, nodelist[2])
      raise NotImplementedError

    raise AssertionError(op_tok)

  def _DictPair(self, p_node):
    # type: (PNode) -> Tuple[expr_t, expr_t]
    """
    dict_pair: (
      Expr_Name [':' test] |
      '[' testlist ']' ':' test
    )
    """
    assert p_node.typ == grammar_nt.dict_pair

    children = p_node.children
    typ = children[0].typ

    if ISNONTERMINAL(typ):  # for sq_string
      raise NotImplementedError

    tok0 = children[0].tok
    id_ = tok0.id

    if id_ == Id.Expr_Name:
      key = expr.Const(tok0)  # type: expr_t
      if len(children) >= 3:
        value = self.Expr(children[2])
      else:
        value = expr.Implicit()

    if id_ == Id.Op_LBracket:  # {[x+y]: 'val'}
      key = self.Expr(children[1])
      value = self.Expr(children[4])
      return key, value

    return key, value

  def _Dict(self, p_node):
    # type: (PNode) -> expr__Dict
    """
    dict: dict_pair (',' dict_pair)* [',']
    """
    if not ISNONTERMINAL(p_node.typ):
      assert p_node.tok.id == Id.Op_RBrace
      return expr.Dict([], [])

    assert p_node.typ == grammar_nt.dict

    keys = []  # type: List[expr_t]
    values = []  # type: List[expr_t]

    children = p_node.children
    n = len(children)
    i = 0
    while i < n:
      key, value = self._DictPair(children[i])
      keys.append(key)
      values.append(value)
      i += 2

    return expr.Dict(keys, values)

  def _Atom(self, children):
    # type: (List[PNode]) -> expr_t
    """Handles alternatives of 'atom' where there is more than one child."""

    tok = children[0].tok
    id_ = tok.id

    if id_ == Id.Op_LParen:
      # atom: '(' [yield_expr|testlist_comp] ')' | ...
      if children[1].tok.id == Id.Op_RParen:
        # () is a tuple
        return expr.Tuple([], expr_context_e.Store)
      else:
        return self.Expr(children[1])

    if id_ == Id.Op_LBracket:
      # atom: ... | '[' [testlist_comp] ']' | ...

      if len(children) == 2:  # []
        return expr.List([], expr_context_e.Store)  # unused expr_context_e

      p_list = children[1].children  # what's between [ and ]

      # [x for x in y]
      if children[1].typ == grammar_nt.testlist_comp:
        return self.Expr(children[1])

      # [1, 2, 3]
      n = len(p_list)
      elts = []
      for i in xrange(0, n, 2):  # skip commas
        p_node = p_list[i]
        elts.append(self.Expr(p_node))

      return expr.List(elts, expr_context_e.Store)  # unused expr_context_e

    if id_ == Id.Op_LBrace:
      return self._Dict(children[1])

    raise NotImplementedError(id_)

  def _Tuple(self, children):
    # type: (List[PNode]) -> expr_t

    # NOTE: We haven't solved the 1, issue.  Gah!  Or ()
    # 1, 2, 3
    n = len(children)
    if n == 1:
      return self.Expr(children[0])
    elts = []
    for i in xrange(0, n, 2):  # skip commas
      p_node = children[i]
      elts.append(self.Expr(p_node))

    return expr.Tuple(elts, expr_context_e.Store)  # unused expr_context_e

  def _CompFor(self, p_node):
    # type: (PNode) -> comprehension
    """
    comp_for: 'for' exprlist 'in' or_test ['if' test_nocond]
    """
    children = p_node.children

    lvalue = self.Expr(children[1])  # Python calls this target
    iterable = self.Expr(children[3])

    if_ = None
    if len(children) >= 6:
      if_ = self.Expr(children[5])

    # TODO: Simplify the node
    ifs = [if_] if if_ else []
    return comprehension(lvalue, iterable, ifs)

  def Expr(self, pnode):
    # type: (PNode) -> expr_t
    """Transform expressions (as opposed to statements)."""
    typ = pnode.typ
    tok = pnode.tok
    children = pnode.children

    if ISNONTERMINAL(typ):
      c = '-' if not children else len(children)
      #log('non-terminal %s %s', nt_name, c)

      if typ == grammar_nt.oil_expr:  # for if/while
        # oil_expr: '(' testlist ')'
        return self.Expr(children[1])

      if typ == grammar_nt.return_expr:  # for if/while
        # return_expr: testlist end_stmt
        return self.Expr(children[0])

      if typ == grammar_nt.place_list:
        return self._AssocBinary(children)

      if typ == grammar_nt.place:
        # place: NAME place_trailer*
        if len(pnode.children) == 1:
          return self.Expr(pnode.children[0])
        raise NotImplementedError

      if typ == grammar_nt.atom:
        if len(children) == 1:
          return self.Expr(children[0])
        return self._Atom(children)

      if typ == grammar_nt.eval_input:
        # testlist_input: testlist NEWLINE* ENDMARKER
        return self.Expr(children[0])

      if typ == grammar_nt.testlist:
        # testlist: test (',' test)* [',']
        # We need tuples for Python's 'var a, b = x' and 'for (a, b in x) {'
        return self._Tuple(children)

      if typ == grammar_nt.test:
        if len(children) == 1:
          return self.Expr(children[0])
        raise NotImplementedError

      if typ == grammar_nt.test_nocond:
        # test_nocond: or_test | lambdef_nocond
        assert len(children) == 1
        return self.Expr(children[0])

      if typ == grammar_nt.or_test:
        if len(children) == 1:
          return self.Expr(children[0])
        raise NotImplementedError

      if typ == grammar_nt.and_test:
        if len(pnode.children) == 1:
          return self.Expr(children[0])
        raise NotImplementedError

      if typ == grammar_nt.not_test:
        if len(pnode.children) == 1:
          return self.Expr(children[0])
        raise NotImplementedError

      if typ == grammar_nt.xor_expr:
        if len(pnode.children) == 1:
          return self.Expr(children[0])
        raise NotImplementedError

      if typ == grammar_nt.and_expr:
        if len(pnode.children) == 1:
          return self.Expr(children[0])
        raise NotImplementedError

      if typ == grammar_nt.argument:
        # argument: ( test [comp_for] |
        #             test '=' test |
        #             '**' test |
        #             '*' test )
        if len(pnode.children) == 1:
          return self.Expr(children[0])
        # TODO:
        raise NotImplementedError

      if typ == grammar_nt.subscript:
        # subscript: test | [test] ':' [test] [sliceop]
        if len(pnode.children) == 1:
          return self.Expr(children[0])
        # TODO:
        raise NotImplementedError

      if typ == grammar_nt.testlist_comp:
        # testlist_comp: (test|star_expr) ( comp_for | (',' (test|star_expr))* [','] )
        if children[1].typ == grammar_nt.comp_for:
          elt = self.Expr(children[0])
          comp = self._CompFor(children[1])
          return expr.ListComp(elt, [comp])

        # (1,)  (1, 2)  etc.
        if children[1].tok.id == Id.Arith_Comma:
          return self._Tuple(children)
        raise NotImplementedError('testlist_comp')

      elif typ == grammar_nt.exprlist:
        # exprlist: (expr|star_expr) (',' (expr|star_expr))* [',']

        if len(children) == 1:
          return self.Expr(children[0])

        # used in for loop, genexpr.
        # TODO: This sould be placelist?  for x, *y ?
        raise NotImplementedError('exprlist')

      elif typ == grammar_nt.arith_expr:
        # expr: term (('+'|'-') term)*
        return self._AssocBinary(children)

      elif typ == grammar_nt.term:
        # term: factor (('*'|'/'|'div'|'mod') factor)*
        return self._AssocBinary(children)

      elif typ == grammar_nt.expr:
        # expr: xor_expr ('|' xor_expr)*
        return self._AssocBinary(children)

      elif typ == grammar_nt.shift_expr:
        # shift_expr: arith_expr (('<<'|'>>') arith_expr)*
        return self._AssocBinary(children)

      elif typ == grammar_nt.comparison:
        # comparison: expr (comp_op expr)*
        return self._AssocBinary(children)

      elif typ == grammar_nt.factor:
        # factor: ('+'|'-'|'~') factor | power
        # the power would have already been reduced
        if len(children) == 1:
          return self.Expr(children[0])
        op, e = children
        assert isinstance(op.tok, token)
        return expr.Unary(op.tok, self.Expr(e))

      elif typ == grammar_nt.power:
        # power: atom trailer* ['^' factor]

        base = self.Expr(children[0])

        # TODO: Handle '^' factor
        n = len(children)
        for i in xrange(1, n):
          pnode = children[i]
          tok = pnode.tok
          base = self._Trailer(base, pnode)

        return base

      elif typ == grammar_nt.array_literal:
        left_tok = children[0].tok

        # Approximation for now.
        tokens = [
            pnode.tok for pnode in children[1:-1] if pnode.tok.id ==
            Id.Lit_Chars
        ]
        items = [expr.Const(t) for t in tokens]  # type: List[expr_t]
        return expr.ArrayLiteral(left_tok, items)

      elif typ == grammar_nt.sh_array_literal:
        left_tok = children[0].tok

        # HACK: When typ is Id.Expr_WordsDummy, the 'tok' field ('opaque')
        # actually has a list of words!
        typ1 = children[1].typ
        assert typ1 == Id.Expr_WordsDummy.enum_id, typ1
        array_words = cast('List[word_t]', children[1].tok)

        return expr.ShellArrayLiteral(left_tok, array_words)

      elif typ == grammar_nt.regex_literal:
        left_tok = children[0].tok

        # Approximation for now.
        tokens = [
            pnode.tok for pnode in children[1:-1] if pnode.tok.id ==
            Id.Expr_Name
        ]
        parts = [regex.Var(t) for t in tokens]  # type: List[regex_t]

        return expr.RegexLiteral(left_tok, regex.Concat(parts))

      elif typ == grammar_nt.command_sub:
        left_tok = children[0].tok

        # Approximation for now.
        tokens = [
            pnode.tok for pnode in children[1:-1] if pnode.tok.id ==
            Id.Lit_Chars
        ]
        words = [
            word.Compound([word_part.Literal(t)]) for t in tokens
        ]  # type: List[word_t]
        return expr.CommandSub(left_tok, command.Simple(words))

      elif typ == grammar_nt.sh_command_sub:
        left_tok = children[0].tok

        # HACK: When typ is Id.Expr_CommandDummy, the 'tok' field ('opaque')
        # actually has a word_part.CommandSub!
        typ1 = children[1].typ
        assert typ1 == Id.Expr_CommandDummy.enum_id, typ1
        cs_part = cast(word_part__CommandSub, children[1].tok)

        # Awkward: the schemas are different
        expr_part = expr.CommandSub(cs_part.left_token, cs_part.command_list)
        expr_part.spids.extend(cs_part.spids)
        return expr_part

      elif typ == grammar_nt.var_sub:
        left_tok = children[0].tok

        return expr.VarSub(left_tok, self.Expr(children[1]))

      elif typ == grammar_nt.dq_string:
        dq_part = cast(expr__DoubleQuoted, children[1].tok)
        return dq_part

      elif typ == grammar_nt.sq_string:
        sq_part = cast(expr__SingleQuoted, children[1].tok)
        return sq_part

      else:
        nt_name = self.number2symbol[typ]
        raise AssertionError(
            "PNode type %d (%s) wasn't handled" % (typ, nt_name))

    else:  # Terminals should have a token
      id_ = tok.id

      if id_ == Id.Expr_Name:
        return expr.Var(tok)

      if id_ in (
          Id.Expr_DecInt, Id.Expr_BinInt, Id.Expr_OctInt, Id.Expr_HexInt,
          Id.Expr_Float):
        return expr.Const(tok)

      if id_ in (Id.Expr_Null, Id.Expr_True, Id.Expr_False):
        return expr.Const(tok)

      from core.meta import IdInstance
      raise NotImplementedError(IdInstance(typ))

  def VarDecl(self, pnode):
    # type: (PNode) -> command__VarDecl
    """Transform an Oil assignment statement."""
    typ = pnode.typ
    children = pnode.children

    # TODO: Fill this in.
    lhs_type = None

    if typ == grammar_nt.oil_var:
      # oil_var: lvalue_list [type_expr] '=' testlist (Op_Semi | Op_Newline)

      #log('len(children) = %d', len(children))

      lvalue = self.Expr(children[0])  # could be a tuple
      #log('lvalue %s', lvalue)

      n = len(children)
      if n == 4:
        op_tok = children[1].tok
        rhs = children[2]
      elif n == 5:
        # TODO: translate type expression
        op_tok = children[2].tok
        rhs = children[3]

      else:
        raise AssertionError(n)

      # The caller should fill in the keyword token.
      return command.VarDecl(None, lvalue, lhs_type, op_tok, self.Expr(rhs))

    if typ == grammar_nt.oil_setvar:
      # oil_setvar: lvalue_list (augassign | '=') testlist (Op_Semi | Op_Newline)
      lvalue = self.Expr(children[0])  # could be a tuple
      op_tok = children[1].tok
      rhs = children[2]
      return command.VarDecl(None, lvalue, lhs_type, op_tok, self.Expr(rhs))

    nt_name = self.number2symbol[typ]
    raise AssertionError(
        "PNode type %d (%s) wasn't handled" % (typ, nt_name))

  def OilForExpr(self, pnode):
    # type: (PNode) -> Tuple[expr_t, expr_t]
    typ = pnode.typ
    children = pnode.children

    # TODO: Distinguish between for-in and for-c
    if typ == grammar_nt.oil_for:
      # oil_for: '(' lvalue_list 'in' testlist ')'
      lvalue = self.Expr(children[1])  # could be a tuple
      iterable = self.Expr(children[3])
      return lvalue, iterable

    nt_name = self.number2symbol[typ]
    raise AssertionError(
        "PNode type %d (%s) wasn't handled" % (typ, nt_name))

  def _Argument(self, pnode):
    # type: (PNode) -> expr_t
    """
    argument: ( test [comp_for] |
                test '=' test |
                '**' test |
                '*' test )
    """
    # Only simple args for now.
    # TODO: Do keyword args and such.
    return self.Expr(pnode)

  def _Arglist(self, children, out):
    # type: (List[PNode], List[expr_t]) -> None
    """
    arglist: argument (',' argument)*  [',']
    """
    n = len(children)
    i = 0
    while i < n:
      result = self._Argument(children[i])
      out.append(result)
      i += 2

  def ArgList(self, pnode):
    # type: (PNode) -> List[expr_t]
    """Transform arg lists.

    oil_arglist: '(' [arglist] ')'
    """
    args = []  # type: List[expr_t]
    if len(pnode.children) == 2:  # f()
      return args

    assert len(pnode.children) == 3, pnode.children
    p = pnode.children[1]  # the X in '( X )'

    assert p.typ == grammar_nt.arglist
    self._Arglist(p.children, args)
    return args

  def _TypeExpr(self, pnode):
    # type: (PNode) -> type_expr_t
    assert pnode.typ == grammar_nt.type_expr, pnode.typ
    return None

  def _Param(self, pnode):
    # type: (PNode) -> param
    """
    param: NAME [type_expr] | '...' NAME | '@' NAME
    """
    #log('pnode: %s', pnode)
    assert pnode.typ == grammar_nt.param

    children = pnode.children
    tok0 = children[0].tok
    n = len(children)
    #tok = pnode.tok

    if tok0.id in (Id.Expr_At,):  # ...
      return param(tok0, children[1].tok, None, None)

    if tok0.id == Id.Expr_Name:
      default = None
      if n > 1 and children[1].tok.id == Id.Arith_Equal:  # f(x = 1+2*3)
        default = self.Expr(children[2])
      elif n > 2 and children[2].tok.id == Id.Arith_Equal:  # f(x Int = 1+2*3)
        default = self.Expr(children[3])
      return param(None, tok0, None, default)

    raise AssertionError(tok0)

  def FuncProc(self, pnode):
    # type: (PNode) -> Tuple[token, List[param], Optional[type_expr_t]]
    typ = pnode.typ
    children = pnode.children

    if typ == grammar_nt.oil_func_proc:
      # oil_func_proc: NAME ['(' params [';' params] ')'] [type_expr] '{'

      name = children[0].tok
      params = []  # type: List[param]
      return_type = None

      if children[1].tok.id == Id.Op_LBrace:  # proc foo {
        return name, params, return_type  # EARLY RETURN

      assert children[1].tok.id == Id.Op_LParen  # proc foo(

      typ2 = children[2].typ
      if typ2 == Id.Op_RParen:  # f()
        next_index = 3
      elif typ2 == grammar_nt.params:  # f(x, y)
        next_index = 4
        # every other one is a comma
        params = [self._Param(c) for c in children[2].children[::2]]
      else:
        raise AssertionError

      if ISNONTERMINAL(children[next_index].typ):
        return_type = self._TypeExpr(children[next_index])
        # otherwise it's Id.Op_LBrace like f() {

      return name, params, return_type

    nt_name = self.number2symbol[typ]
    raise AssertionError(
        "PNode type %d (%s) wasn't handled" % (typ, nt_name))
