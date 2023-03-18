"""
expr_to_ast.py
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Id_t, Id_str
from _devbuild.gen.syntax_asdl import (
    Token, loc, loc_t,
    double_quoted, single_quoted, simple_var_sub, braced_var_sub, command_sub,
    sh_array_literal,
    command, command_t,
    expr, expr_e, expr_t, expr__Var, expr__Dict, expr_context_e,
    re, re_t, re_repeat, re_repeat_t, class_literal_term, class_literal_term_t,
    posix_class, perl_class,
    name_type, place_expr, place_expr_e, place_expr_t, type_expr_t,
    comprehension, subscript, attribute, proc_sig, proc_sig_t, param,
    named_arg, ArgList, TypedParam, UntypedParam,
    variant, variant_type, variant_type_t,
)
from _devbuild.gen import grammar_nt
from core.pyerror import log, p_die
from frontend import lexer

from typing import TYPE_CHECKING, List, Tuple, Optional, cast
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import (
      command__VarDecl, command__PlaceMutation, command__Func, command__Data,
      command__Enum, command__Class, command__Import,
      command__CommandList,
  )
  from pgen2.grammar import Grammar
  from pgen2.pnode import PNode

_ = log


PERL_CLASSES = {
    'd': 'd',
    'w': 'w', 'word': 'w',
    's': 's',
}
# https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap09.html
POSIX_CLASSES = [
    'alnum', 'cntrl', 'lower', 'space',
    'alpha', 'digit', 'print', 'upper',
    'blank', 'graph', 'punct', 'xdigit',
]
# NOTE: There are also things like \p{Greek} that we could put in the
# "non-sigil" namespace.

RANGE_POINT_TOO_LONG = "Range start/end shouldn't have more than one character"


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

    Examples:
      xor_expr: and_expr ('xor' and_expr)*
      term: factor (('*'|'/'|'%'|'div') factor)*

    We don't care if it's (1+2)+3 or 1+(2+3).
    """
    # Note: Compare the iteractive com_binary() method in
    # opy/compiler2/transformer.py.

    n = len(children)
    if n == 1:
      return self.Expr(children[0])

    # left is evaluated first
    left = self.Expr(children[0])
    op = children[1]

    if n == 3:
      right = self.Expr(children[2])
    else:
      right = self._AssocBinary(children[2:])  # Recursive call

    return expr.Binary(op.tok, left, right)

  def _Trailer(self, base, p_trailer):
    # type: (expr_t, PNode) -> expr_t
    """
    trailer: (
      '(' [arglist] ')' | '[' subscriptlist ']'
    | '.' NAME | '->' NAME | '::' NAME
    )
    """
    children = p_trailer.children
    op_tok = children[0].tok

    # TODO: Need to process ALL the trailers, e.g. f(x, y)[1, 2](x, y)

    if op_tok.id == Id.Op_LParen:
      lparen = children[0].tok
      rparen = children[-1].tok
      arglist = ArgList(lparen, [], [], rparen)
      if len(children) == 2:  # ()
        return expr.FuncCall(base, arglist)

      p = children[1]  # the X in ( X )
      assert p.typ == grammar_nt.arglist  # f(x, y)
      self._Arglist(p.children, arglist)
      return expr.FuncCall(base, arglist)

    if op_tok.id == Id.Op_LBracket:
      p_args = children[1]
      assert p_args.typ == grammar_nt.subscriptlist
      indices = []  # type: List[expr_t]
      n = len(p_args.children)
      for i in xrange(0, n, 2):  # was children[::2]
        a = p_args.children[i]
        indices.append(self._Subscript(a.children))
      return subscript(base, indices)

    if op_tok.id in (Id.Expr_Dot, Id.Expr_RArrow, Id.Expr_DColon):
      attr = children[1].tok  # will be Id.Expr_Name
      return attribute(base, op_tok, attr, expr_context_e.Store)

    raise AssertionError(Id_str(op_tok.id))

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
      # Note: Could inline these cases instead of going through self.Expr.
      if typ == grammar_nt.sq_string:
        key = self.Expr(children[0])  # type: expr_t
      elif typ == grammar_nt.dq_string:
        key = self.Expr(children[0])

      value = self.Expr(children[2])
      return key, value

    tok0 = children[0].tok
    id_ = tok0.id

    if id_ == Id.Expr_Name:
      key = expr.Const(tok0)
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

    dict2: dict_pair (comma_newline dict_pair)* [comma_newline]
    """
    if not ISNONTERMINAL(p_node.typ):
      assert p_node.tok.id == Id.Op_RBrace
      return expr.Dict([], [])

    #assert p_node.typ == grammar_nt.dict

    keys = []  # type: List[expr_t]
    values = []  # type: List[expr_t]

    n = len(p_node.children)
    for i in xrange(0, n, 2):
      key, value = self._DictPair(p_node.children[i])
      keys.append(key)
      values.append(value)

    return expr.Dict(keys, values)

  def _Tuple(self, children):
    # type: (List[PNode]) -> expr_t

    n = len(children)

    # (x) -- not a tuple
    if n == 1:
      return self.Expr(children[0])

    # x, and (x,) aren't allowed
    if n == 2:
      p_die('Write singleton tuples with tup(), not a trailing comma',
            children[1].tok)

    elts = []  # type: List[expr_t]
    for i in xrange(0, n, 2):  # skip commas
      p_node = children[i]
      elts.append(self.Expr(p_node))

    return expr.Tuple(elts, expr_context_e.Store)  # unused expr_context_e

  def _TestlistComp(self, p_node, id0):
    # type: (PNode, Id_t) -> expr_t
    """
    testlist_comp: (test|star_expr) ( comp_for | (',' (test|star_expr))* [','] )
    """
    assert p_node.typ == grammar_nt.testlist_comp
    children = p_node.children
    n = len(children)
    if n > 1 and children[1].typ == grammar_nt.comp_for:
      elt = self.Expr(children[0])
      comp = self._CompFor(children[1])
      if id0 == Id.Op_LParen:
        return expr.GeneratorExp(elt, [comp])
      if id0 == Id.Op_LBracket:
        return expr.ListComp(elt, [comp])
      raise AssertionError()

    if id0 == Id.Op_LParen:
      if len(children) == 1:  # parenthesized expression like (x+1) or (x)
        return self.Expr(children[0])

      # (1,)  (1, 2)  etc.
      if children[1].tok.id == Id.Arith_Comma:
        return self._Tuple(children)

      raise NotImplementedError('testlist_comp')

    if id0 == Id.Op_LBracket:
      elts = []  # type: List[expr_t]
      for i in xrange(0, n, 2):  # skip commas
        elts.append(self.Expr(children[i]))

      return expr.List(elts, expr_context_e.Store)  # unused expr_context_e

    raise AssertionError(Id_str(id0))

  def _Atom(self, children):
    # type: (List[PNode]) -> expr_t
    """Handles alternatives of 'atom' where there is more than one child."""

    tok = children[0].tok
    id_ = tok.id
    n = len(children)

    if id_ == Id.Op_LParen:
      # atom: '(' [yield_expr|testlist_comp] ')' | ...
      if n == 2:  # () is a tuple
        assert children[1].tok.id == Id.Op_RParen, children[1]
        return expr.Tuple([], expr_context_e.Store)

      return self._TestlistComp(children[1], id_)

    if id_ == Id.Op_LBracket:
      # atom: ... | '[' [testlist_comp] ']' | ...

      if n == 2:  # []
        assert children[1].tok.id == Id.Op_RBracket, children[1]
        return expr.List([], expr_context_e.Store)  # unused expr_context_e

      return self._TestlistComp(children[1], id_)

    if id_ == Id.Op_LBrace: 
      # atom: ... | '{' [Op_Newline] [dict] '}'
      i = 1
      if children[i].tok.id == Id.Op_Newline:
        i += 1
      return self._Dict(children[i])

    if id_ == Id.Arith_Slash:
      r = self._Regex(children[1])
      flags = []  # type: List[Token]
      # TODO: Parse translation preference.
      trans_pref = None  # type: Token
      return expr.RegexLiteral(children[0].tok, r, flags, trans_pref)

    if id_ == Id.Expr_Func:
      # STUB.  This should really be a Func, not Lambda.
      return expr.Lambda([], expr.Implicit())

    raise NotImplementedError(Id_str(id_))

  def _NameTypeList(self, p_node):
    # type: (PNode) -> List[name_type]
    """
    name_type_list: name_type (',' name_type)*
    """
    assert p_node.typ == grammar_nt.name_type_list
    results = []  # type: List[name_type]

    n = len(p_node.children)
    for i in xrange(0, n, 2):  # was children[::2]
      p = p_node.children[i]
      children = p.children

      if len(children) == 2:
        typ = self._TypeExpr(children[1])
      else:
        typ = None

      node = name_type(children[0].tok, typ)
      results.append(node)
    return results

  def _CompFor(self, p_node):
    # type: (PNode) -> comprehension
    """
    comp_for: 'for' exprlist 'in' or_test ['if' or_test]
    """
    children = p_node.children

    lhs = self._NameTypeList(children[1])  # Python calls this target
    iterable = self.Expr(children[3])

    if len(children) >= 6:
      cond = self.Expr(children[5])
    else:
      cond = None

    return comprehension(lhs, iterable, cond)

  def _CompareChain(self, children):
    # type: (List[PNode]) -> expr_t
    """
    comparison: expr (comp_op expr)*
    """
    cmp_ops = []  # type: List[Token]
    comparators = []  # type: List[expr_t]
    left = self.Expr(children[0])

    i = 1
    n = len(children)
    while i < n:
      op_children = children[i].children
      op = op_children[0].tok
      if len(op_children) == 2:
        # Blame the first token, and change its type
        if op.id == Id.Expr_Not:  # not in
          op.id = Id.Node_NotIn
        elif op.id == Id.Expr_Is:  # is not
          op.id = Id.Node_IsNot
        else:
          raise AssertionError()
      else:
        # is, <, ==, etc.
        pass

      cmp_ops.append(op)
      i += 1
      comparators.append(self.Expr(children[i]))
      i += 1
    return expr.Compare(left, cmp_ops, comparators)

  def _Subscript(self, children):
    # type: (List[PNode]) -> expr_t
    """
    subscript: expr | [expr] ':' [expr]
    """
    typ0 = children[0].typ

    n = len(children)

    if ISNONTERMINAL(typ0):
      if n == 3:     # a[1:2]
        lower = self.Expr(children[0])
        upper = self.Expr(children[2])
      elif n == 2:   # a[1:]
        lower = self.Expr(children[0])
        upper = None
      else:          # a[1]
        return self.Expr(children[0])
    else:
      assert children[0].tok.id == Id.Arith_Colon
      lower = None
      if n == 1:     # a[:]
        upper = None
      else:          # a[:3]
        upper = self.Expr(children[1])
    return expr.Slice(lower, upper)

  def Expr(self, pnode):
    # type: (PNode) -> expr_t
    """Transform expressions (as opposed to statements)."""
    typ = pnode.typ
    tok = pnode.tok
    children = pnode.children

    if ISNONTERMINAL(typ):

      #
      # Oil Entry Points / Additions
      #

      if typ == grammar_nt.oil_expr:  # for if/while
        # oil_expr: '(' testlist ')'
        return self.Expr(children[1])

      if typ == grammar_nt.command_expr:
        # return_expr: testlist end_stmt
        return self.Expr(children[0])

      #
      # Python-like Expressions / Operators
      #

      if typ == grammar_nt.atom:
        if len(children) == 1:
          return self.Expr(children[0])
        return self._Atom(children)

      if typ == grammar_nt.testlist:
        # testlist: test (',' test)* [',']
        return self._Tuple(children)

      if typ == grammar_nt.test:
        # test: or_test ['if' or_test 'else' test] | lambdef
        if len(children) == 1:
          return self.Expr(children[0])

        # TODO: Handle lambdef

        test = self.Expr(children[2])
        body = self.Expr(children[0])
        orelse = self.Expr(children[4])
        return expr.IfExp(test, body, orelse)

      if typ == grammar_nt.lambdef:
        # lambdef: '|' [name_type_list] '|' test

        n = len(children)
        if n == 4:
          params = self._NameTypeList(children[1])
        else:
          params = []

        body = self.Expr(children[n-1])
        return expr.Lambda(params, body)

      #
      # Operators with Precedence
      #

      if typ == grammar_nt.or_test:
        # or_test: and_test ('or' and_test)*
        return self._AssocBinary(children)

      if typ == grammar_nt.and_test:
        # and_test: not_test ('and' not_test)*
        return self._AssocBinary(children)

      if typ == grammar_nt.not_test:
        # not_test: 'not' not_test | comparison
        if len(children) == 1:
          return self.Expr(children[0])

        op_tok = children[0].tok  # not
        return expr.Unary(op_tok, self.Expr(children[1]))

      elif typ == grammar_nt.comparison:
        if len(children) == 1:
          return self.Expr(children[0])

        return self._CompareChain(children)

      elif typ == grammar_nt.range_expr:
        n = len(children)
        if n == 1:
          return self.Expr(children[0])

        if n == 3:
          return expr.Range(
              self.Expr(children[0]),
              self.Expr(children[2])
          )

        raise AssertionError(n)

      elif typ == grammar_nt.expr:
        # expr: xor_expr ('|' xor_expr)*
        return self._AssocBinary(children)

      if typ == grammar_nt.xor_expr:
        # xor_expr: and_expr ('xor' and_expr)*
        return self._AssocBinary(children)

      if typ == grammar_nt.and_expr:  # a & b
        # and_expr: shift_expr ('&' shift_expr)*
        return self._AssocBinary(children)

      elif typ == grammar_nt.shift_expr:
        # shift_expr: arith_expr (('<<'|'>>') arith_expr)*
        return self._AssocBinary(children)

      elif typ == grammar_nt.arith_expr:
        # arith_expr: term (('+'|'-') term)*
        return self._AssocBinary(children)

      elif typ == grammar_nt.term:
        # term: factor (('*'|'/'|'div'|'mod') factor)*
        return self._AssocBinary(children)

      elif typ == grammar_nt.factor:
        # factor: ('+'|'-'|'~') factor | power
        # the power would have already been reduced
        if len(children) == 1:
          return self.Expr(children[0])

        assert len(children) == 2
        op = children[0]
        e = children[1]

        assert isinstance(op.tok, Token)
        return expr.Unary(op.tok, self.Expr(e))

      elif typ == grammar_nt.power:
        # power: atom trailer* ['**' factor]

        node = self.Expr(children[0])
        if len(children) == 1:  # No trailers
          return node

        n = len(children)
        i = 1
        while i < n and ISNONTERMINAL(children[i].typ):
          node = self._Trailer(node, children[i])
          i += 1
        if node.tag_() == expr_e.Attribute:
          # Support a.startswith(b) but not obj.field
          attr_node = cast(attribute, node)
          if attr_node.op.id == Id.Expr_Dot:
            p_die("obj.field isn't valid, but obj.method() is",
                  attr_node.op)

        if i != n:  # ['**' factor]
          op_tok = children[i].tok
          assert op_tok.id == Id.Arith_DStar, op_tok
          factor = self.Expr(children[i+1])
          node = expr.Binary(op_tok, node, factor)

        return node

      elif typ == grammar_nt.oil_expr_sub:
        return self.Expr(children[0])

      #
      # Oil Lexer Modes
      #

      elif typ == grammar_nt.sh_array_literal:
        return cast(sh_array_literal, children[1].tok)

      elif typ == grammar_nt.sh_command_sub:
        return cast(command_sub, children[1].tok)

      elif typ == grammar_nt.braced_var_sub:
        return cast(braced_var_sub, children[1].tok)

      elif typ == grammar_nt.dq_string:
        return cast(double_quoted, children[1].tok)

      elif typ == grammar_nt.sq_string:
        return cast(single_quoted, children[1].tok)

      elif typ == grammar_nt.simple_var_sub:
        tok = children[0].tok

        if tok.id == Id.VSub_DollarName:  # $foo is disallowed
          bare = tok.tval[1:]
          p_die('In expressions, remove $ and use `%s`, or sometimes "$%s"' %
                (bare, bare), tok)

        # $? is allowed
        return simple_var_sub(tok, lexer.TokenSliceLeft(tok, 1))

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

      if id_ in (Id.Expr_Null, Id.Expr_True, Id.Expr_False,
                 Id.Char_OneChar, Id.Char_UBraced, Id.Char_Pound):
        return expr.Const(tok)

      raise NotImplementedError(Id_str(id_))

  def _ArrayItem(self, p_node):
    # type: (PNode) -> expr_t
    assert p_node.typ == grammar_nt.array_item

    child0 = p_node.children[0]
    typ0 = child0.typ
    if ISNONTERMINAL(typ0):
      return self.Expr(child0)
    else:
      if child0.tok.id == Id.Op_LParen:  # (x+1)
        return self.Expr(p_node.children[1])
      return self.Expr(child0)  # $1 ${x} etc.

  def _PlaceList(self, p_node):
    # type: (PNode) -> List[place_expr_t]
    """
    place_list: expr (',' expr)*
    """
    assert p_node.typ == grammar_nt.place_list
    places = []  # type: List[place_expr_t]
    n = len(p_node.children)
    for i in xrange(0, n, 2):  # was children[::2]
      p = p_node.children[i]
      e = self.Expr(p)
      UP_e = e
      tag = e.tag_()
      if tag == expr_e.Var:  # COMPATIBILITY hack
        e = cast(expr__Var, UP_e)
        places.append(place_expr.Var(e.name))
      elif tag in (
          place_expr_e.Var, place_expr_e.Subscript, place_expr_e.Attribute):
        places.append(cast(place_expr_t, UP_e))
      else:
        # This blame mechanism seems to work.  Otherwise we don't have a method
        # to blame an arbitrary expr_t.
        blame = cast(loc_t, p.tok) if p.tok else loc.Missing()  # type: loc_t
        p_die("Can't assign to this expression", blame)
    return places

  def MakeVarDecl(self, p_node):
    # type: (PNode) -> command__VarDecl
    """
    oil_var_decl: name_type_list '=' testlist end_stmt
    """
    typ = p_node.typ
    children = p_node.children
    assert typ == grammar_nt.oil_var_decl

    #log('len(children) = %d', len(children))
    lhs = self._NameTypeList(children[0])  # could be a tuple
    rhs = self.Expr(children[2])

    # The caller should fill in the keyword token.
    return command.VarDecl(None, lhs, rhs)

  def MakePlaceMutation(self, p_node):
    # type: (PNode) -> command__PlaceMutation
    """
    oil_place_mutation: place_list (augassign | '=') testlist end_stmt
    """
    typ = p_node.typ
    children = p_node.children
    assert typ == grammar_nt.oil_place_mutation

    place_list = self._PlaceList(children[0])  # could be a tuple
    op_tok = children[1].tok
    rhs = self.Expr(children[2])
    return command.PlaceMutation(None, place_list, op_tok, rhs)

  def OilForExpr(self, pnode):
    # type: (PNode) -> Tuple[List[name_type], expr_t]
    typ = pnode.typ
    children = pnode.children

    if typ == grammar_nt.oil_for:
      # oil_for: '(' lvalue_list 'in' testlist ')'
      lhs = self._NameTypeList(children[1])  # could be a tuple
      iterable = self.Expr(children[3])
      return lhs, iterable

    nt_name = self.number2symbol[typ]
    raise AssertionError(
        "PNode type %d (%s) wasn't handled" % (typ, nt_name))

  def _Argument(self, p_node, do_named, arglist):
    # type: (PNode, bool, ArgList) -> None
    """
    argument: (
      test [comp_for]
      # named arg
    | test '=' test
      # var args
    | '...' test
    )
    """
    positional = arglist.positional
    named = arglist.named

    assert p_node.typ == grammar_nt.argument, p_node
    children = p_node.children
    n = len(children)
    if n == 1:
      arg = self.Expr(children[0])
      positional.append(arg)
      return

    if n == 2:
      # Note: We allow multiple spreads, just like Julia.  They are
      # concatenated as in lists and dicts.
      if children[0].tok.id == Id.Expr_Ellipsis:
        spread_expr = self.Expr(children[1])
        if do_named:
          # Implicit spread with name = None
          named.append(named_arg(None, spread_expr))
        else:
          positional.append(expr.Spread(spread_expr, expr_context_e.Store))
        return

      if children[1].typ == grammar_nt.comp_for:
        elt = self.Expr(children[0])
        comp = self._CompFor(children[1])
        arg = expr.GeneratorExp(elt, [comp])
        positional.append(arg)
        return

      raise AssertionError()

    if n == 3:
      n1 = named_arg(children[0].tok, self.Expr(children[2]))
      named.append(n1)
      return

    raise NotImplementedError()

  def _Arglist(self, children, arglist):
    # type: (List[PNode], ArgList) -> None
    """
    arglist: argument (',' argument)* [','] [';' argument (',' argument)* [',']]
    """
    do_named = False
    for p_child in children:
      if ISNONTERMINAL(p_child.typ):
        self._Argument(p_child, do_named, arglist)
      elif p_child.tok.id == Id.Op_Semi:
        do_named = True

  def ToArgList(self, pnode, arglist):
    # type: (PNode, ArgList) -> None
    """Transform arg lists.

    oil_arglist: '(' [arglist] ')'
    """
    if len(pnode.children) == 2:  # f()
      return

    assert len(pnode.children) == 3, pnode.children
    p = pnode.children[1]  # the X in '( X )'

    assert p.typ == grammar_nt.arglist
    self._Arglist(p.children, arglist)

  def _TypeExpr(self, pnode):
    # type: (PNode) -> type_expr_t
    assert pnode.typ == grammar_nt.type_expr, pnode.typ
    return None

  def _TypeExprList(self, pnode):
    # type: (PNode) -> List[type_expr_t]
    assert pnode.typ == grammar_nt.type_expr_list, pnode.typ
    return None

  def _ProcParam(self, pnode):
    # type: (PNode) -> Tuple[Optional[Token], Token, Optional[Token], Optional[expr_t]]
    """
    proc_param: (
        ':' Expr_Name | '@' Expr_Name |
        Expr_Name [ Expr_Name ] ['=' expr]  # type is either Expr or Block
    )
    """
    assert pnode.typ == grammar_nt.proc_param

    children = pnode.children
    tok0 = children[0].tok
    n = len(children)

    prefix = None  # type: Optional[Token]
    name = None  # type: Optional[Token]
    typ = None  # type: Optional[Token]
    default_val = None  # type: Optional[expr_t]

    if tok0.id in (Id.Arith_Colon, Id.Expr_At):
      prefix = tok0
      name = children[1].tok
      return prefix, name, typ, default_val

    name = children[0].tok
    if n == 1:
      return prefix, name, typ, default_val

    i = 1
    tok1 = children[1].tok
    if tok1.id == Id.Expr_Name:
      typ = tok1
      i += 1

    if i + 1 == n - 1:
      assert children[i].tok.id == Id.Arith_Equal
      default_val = self.Expr(children[i+1])
    return prefix, name, typ, default_val

  def _ProcParams(self, p_node):
    # type: (PNode) -> proc_sig_t
    """
    proc_params: (proc_param ',')* [ proc_param  [','] ]
    """
    children = p_node.children
    n = len(children)

    untyped = []  # type: List[UntypedParam]
    rest = None  # type: Optional[Token]
    typed = []  # type: List[TypedParam]

    state = 0

    i = 0
    while i < n:
      prefix, name, typ, default_val = self._ProcParam(children[i])

      # TODO: enforce the order of params.  It should look like
      # untyped* rest? typed*, which is while / if / while!
      if prefix and prefix.id == Id.Expr_At:
        rest = name
      elif typ is None:
        untyped.append(UntypedParam(prefix, name, default_val))
      else:
        if typ.tval not in ('Expr', 'Block'):
          p_die('proc param types should be Expr or Block', typ)
        typed.append(TypedParam(name, typ, default_val))

      i += 2

    return proc_sig.Closed(untyped, rest, typed)

  def _FuncParam(self, pnode):
    # type: (PNode) -> param
    """
    func_param: Expr_Name [type_expr] ['=' expr] | '...' Expr_Name
    """
    assert pnode.typ == grammar_nt.func_param

    children = pnode.children
    tok0 = children[0].tok
    n = len(children)

    if tok0.id == Id.Expr_Name:
      default_val = None  # type: expr_t
      type_ = None  # type: type_expr_t
      if n > 1 and children[1].tok.id == Id.Arith_Equal:  # f(x = 1+2*3)
        default_val = self.Expr(children[2])
      elif n > 2 and children[2].tok.id == Id.Arith_Equal:  # f(x Int = 1+2*3)
        default_val = self.Expr(children[3])
      prefix_tok = None  # type: Token
      return param(prefix_tok, tok0, type_, default_val)

    raise AssertionError(Id_str(tok0.id))

  def _FuncParams(self, p_node):
    # type: (PNode) -> Tuple[List[param], Optional[Token]]
    """
    func_params: [func_param] (',' func_param)* [',' '...' Expr_Name]
    """
    params = []  # type: List[param]
    splat = None  # type: Optional[Token]

    children = p_node.children
    n = len(children)
    for i in xrange(n):
      p = children[i]
      if ISNONTERMINAL(p.typ):
        params.append(self._FuncParam(p))
      elif p.tok.id == Id.Expr_Ellipsis:
        splat = children[i+1].tok

    return params, splat

  def Proc(self, pnode):
    # type: (PNode) -> proc_sig_t
    """
    oil_proc: ['(' [proc_params] ')'] '{'
    """
    typ = pnode.typ
    children = pnode.children
    assert typ == grammar_nt.oil_proc

    n = len(children)
    if n == 1:  # proc f { 
      sig = proc_sig.Open()  # type: proc_sig_t
    elif n == 3:  # proc f () {
      sig = proc_sig.Closed.CreateNull(alloc_lists=True)  # no params
    elif n == 4:  # proc f [foo, bar='z', @args] {
      sig = self._ProcParams(children[1])
    else:
      raise AssertionError(n)

    return sig

  def func_item(self, node):
    # type: (PNode) -> command_t
    """
    func_item: (
      ('var' | 'const') name_type_list '=' testlist  # oil_var_decl

      # TODO: for, if/switch, with, break/continue/return, try/throw, etc.
    | 'while' test suite
    | 'for' name_type_list 'in' test suite
    | flow_stmt
    | 'set' place_list (augassign | '=') testlist  # oil_place_mutation
      # x  f(x)  etc.
      #
      # And x = 1.  Python uses the same "hack" to fit within pgen2.  It also
      # supports a = b = 1, which we don't want.
      #
      # And echo 'hi' 'there'
      #
      # TODO: expr_to_ast needs to validate this
    | testlist (['=' testlist] | tea_word*)
    )
    """
    if node.tok.id == Id.Expr_While:
      return command.While(self.Expr(node.children[1]), self._Suite(node.children[2]))
    elif node.tok.id == Id.Expr_For:
      return command.For(
          self._NameTypeList(node.children[1]),
          self.Expr(node.children[3]),
          self._Suite(node.children[4])
        )
    elif node.tok.id == Id.Expr_Break:
      return command.Break()
    elif node.tok.id == Id.Expr_Continue:
      return command.Continue()
    elif node.tok.id == Id.Expr_Return:
      # 'return' [testlist]
      if len(node.children) == 1:
        return command.Return(None)
      else:
        return command.Return(self.Expr(node.children[1]))
    elif node.tok.id == Id.Expr_Name:
      # TODO: turn echo 'hi' into AST
      return command.NoOp()
    else:
      raise NotImplementedError(Id_str(node.tok.id))

  def func_items(self, pnode):
    # type: (PNode) -> List[command_t]
    """
    func_items: func_item (semi_newline func_item)* [semi_newline]
    """
    # Rewrite of
    # return [self.func_item(item) for item in pnode.children[::2]]
    # Unfortunately mycpp doesn't support the stride.

    result = []  # type: List[command_t]
    n = len(pnode.children)
    for i in xrange(0, n, 2):
      result.append(self.func_item(pnode.children[i]))
    return result

  def _Suite(self, pnode):
    # type: (PNode) -> command__CommandList
    """
    suite: '{' [Op_Newline] [func_items] '}'
    """
    n = len(pnode.children)

    if n == 2:  # {}
      return command.CommandList([])

    if n == 3:
      if pnode.children[1].typ == grammar_nt.func_items:  # { func_items }
        items_index = 1
      else:
        return command.CommandList([])

    if n == 4:  # { Op_Newline func_items }
      items_index = 2

    return command.CommandList(self.func_items(pnode.children[items_index]))

  def TeaFunc(self, pnode, out):
    # type: (PNode, command__Func) -> None
    """
    tea_func: (
      '(' [func_params] [';' func_params] ')' [type_expr_list]
      suite
    )
    """
    assert pnode.typ == grammar_nt.tea_func
    children = pnode.children
    assert children[0].tok.id == Id.Op_LParen  # proc foo(

    pos = 1
    typ2 = children[pos].typ
    if ISNONTERMINAL(typ2):
      assert typ2 == grammar_nt.func_params, children[pos]  # f(x, y)
      # every other one is a comma
      out.pos_params, out.pos_splat = self._FuncParams(children[pos])
      pos += 1

    id_ = children[pos].tok.id
    if id_ == Id.Op_RParen:  # f()
      pos += 1 
    elif id_ == Id.Op_Semi:  # f(; a)
      out.named_params, out.named_splat = self._FuncParams(children[pos+1])
      pos += 3

    if children[pos].typ == grammar_nt.type_expr_list:
      out.return_types = self._TypeExprList(children[pos])
      pos += 1

    out.body = self._Suite(children[pos])

  def NamedFunc(self, pnode, out):
    # type: (PNode, command__Func) -> None
    """
    named_func: Expr_Name tea_func
    """
    assert pnode.typ == grammar_nt.named_func
    children = pnode.children

    out.name = children[0].tok
    self.TeaFunc(children[1], out)

  def _DataParams(self, p_node):
    # type: (PNode) -> List[param]
    """
    data_params: (func_param ',')* [ func_param [','] ]
    """
    params = []  # type: List[param]

    children = p_node.children
    n = len(children)
    for i in xrange(0, n, 2):
      params.append(self._FuncParam(children[i]))

    return params

  def Data(self, pnode, out):
    # type: (PNode, command__Data) -> None
    """
    tea_data: Expr_Name '(' [data_params] ')'
    """
    assert pnode.typ == grammar_nt.tea_data
    children = pnode.children

    out.name = children[0].tok

    assert children[1].tok.id == Id.Op_LParen  # data foo(
    #print(pnode)
    if ISNONTERMINAL(children[2].typ):
      out.params = self._DataParams(children[2])

  def _VariantType(self, pnode):
    # type: (PNode) -> variant_type_t
    """
    variant_type: Expr_Symbol | '(' data_params ')' 
    """
    n = len(pnode.children)
    if n == 1:
      return variant_type.Ref(pnode.children[0].tok)
    else:
      assert n == 3, pnode
      return variant_type.Anon(self._DataParams(pnode.children[1]))

  def _Variant(self, pnode):
    # type: (PNode) -> variant
    """
    variant: Expr_Name [ variant_type ]
    """
    assert pnode.typ == grammar_nt.variant, pnode
    t = None  # type: variant_type_t
    if len(pnode.children) == 2:
      t = self._VariantType(pnode.children[1])
    return variant(pnode.children[0].tok, t)

  def Enum(self, pnode, out):
    # type: (PNode, command__Enum) -> None
    """
    tea_enum: Expr_Name '{' [Op_Newline] (variant variant_end)* [ variant [variant_end] ] '}'
    """
    assert pnode.typ == grammar_nt.tea_enum
    children = pnode.children

    out.name = children[0].tok

    assert children[1].tok.id == Id.Op_LBrace  # enum op {

    start = 2
    if children[start].tok.id == Id.Op_Newline:
      start = 3

    n = len(children)
    for i in xrange(start, n-1, 2):  # skip commas
      p_node = children[i]
      out.variants.append(self._Variant(p_node))

  def Class(self, pnode, out):
    # type: (PNode, command__Class) -> None
    """
    tea_class: Expr_Name [':' Expr_Name ] '{' class_items '}'
    """
    assert pnode.typ == grammar_nt.tea_class
    children = pnode.children

    out.name = children[0].tok

    #assert children[1].tok.id == Id.Op_LBrace  # enum op {
    return
    #n = len(children)
    #for i in xrange(2, n-1, 2):  # skip commas
    #  p_node = children[i]
    #  out.variants.append(self._Variant(p_node))

  def Import(self, pnode, out):
    # type: (PNode, command__Import) -> None
    """
    tea_import: (
      sq_string ['as' Expr_Name]
      (import_name ',')* [ import_name [','] ]
    )
    """
    assert pnode.typ == grammar_nt.tea_import
    children = pnode.children

    typ = children[0].typ
    if ISNONTERMINAL(typ):
      if typ == grammar_nt.sq_string:
        sq_part = cast(single_quoted, children[0].children[1].tok)
        out.path = sq_part

  #
  # Regex Language
  #

  def _RangeChar(self, p_node):
    # type: (PNode) -> Token
    """
    An endpoint of a range (single char)

    range_char: Expr_Name | Expr_DecInt | sq_string | char_literal
                a-z         0-9           'a'-'z'     \x00-\xff
    """
    assert p_node.typ == grammar_nt.range_char, p_node
    children = p_node.children
    typ = children[0].typ
    if ISNONTERMINAL(typ):
      # 'a' in 'a'-'b'
      if typ == grammar_nt.sq_string:
        sq_part = cast(single_quoted, children[0].children[1].tok)
        tokens = sq_part.tokens
        if len(tokens) > 1:  # Can happen with multiline single-quoted strings
          p_die(RANGE_POINT_TOO_LONG, loc.WordPart(sq_part))
        if len(tokens[0].tval) > 1:
          p_die(RANGE_POINT_TOO_LONG, loc.WordPart(sq_part))
        return tokens[0]

      if typ == grammar_nt.char_literal:
        tok = children[0].children[0].tok
        return tok

      raise NotImplementedError()
    else:
      # Expr_Name or Expr_DecInt
      tok = p_node.tok
      if tok.id in (Id.Expr_Name, Id.Expr_DecInt):
        # For the a in a-z, 0 in 0-9
        if len(tok.tval) != 1:
          p_die(RANGE_POINT_TOO_LONG, tok)
        return tok

      raise NotImplementedError()

  def _NonRangeChars(self, p_node):
    # type: (PNode) -> class_literal_term_t
    """
    \" \u1234 '#'
    """
    assert p_node.typ == grammar_nt.range_char, p_node
    children = p_node.children
    typ = children[0].typ
    if ISNONTERMINAL(typ):
      p_child = children[0]
      if typ == grammar_nt.braced_var_sub:
        return cast(braced_var_sub, p_child.children[1].tok)

      if typ == grammar_nt.dq_string:
        return cast(double_quoted, p_child.children[1].tok)

      if typ == grammar_nt.sq_string:
        return cast(single_quoted, p_child.children[1].tok)

      if typ == grammar_nt.simple_var_sub:
        tok = children[0].tok
        return simple_var_sub(tok, lexer.TokenSliceLeft(tok, 1))

      if typ == grammar_nt.char_literal:
        return class_literal_term.CharLiteral(children[0].tok)

      raise NotImplementedError()
    else:
      # Look up PerlClass and PosixClass
      return self._NameInClass(None, children[0].tok)

  def _ClassLiteralTerm(self, p_node):
    # type: (PNode) -> class_literal_term_t
    """
    class_literal_term: (
      range_char ['-' range_char ]
    | '~' Expr_Name
      # $mychars or ${mymodule.mychars}
    | simple_var_sub | braced_var_sub
      # e.g. 'abc' or "abc$mychars" 
    | dq_string
      ...
    """
    assert p_node.typ == grammar_nt.class_literal_term, p_node

    children = p_node.children
    typ = children[0].typ

    if ISNONTERMINAL(typ):
      p_child = children[0]
      if typ == grammar_nt.simple_var_sub:
        tok = p_child.children[0].tok
        return simple_var_sub(tok, lexer.TokenSliceLeft(tok, 1))

      if typ == grammar_nt.braced_var_sub:
        return cast(braced_var_sub, p_child.children[1].tok)

      if typ == grammar_nt.dq_string:
        return cast(double_quoted, p_child.children[1].tok)

      n = len(children)

      if n == 1 and typ == grammar_nt.range_char:
        return self._NonRangeChars(children[0])

      # 'a'-'z' etc.
      if n == 3 and children[1].tok.id == Id.Arith_Minus:
        start = self._RangeChar(children[0])
        end = self._RangeChar(children[2])
        return class_literal_term.Range(start, end)

    else:
      if children[0].tok.id == Id.Expr_Bang:
        return self._NameInClass(children[0].tok, children[1].tok)

      raise AssertionError(children[0].tok.id)

    nt_name = self.number2symbol[typ]
    raise NotImplementedError(nt_name)

  def _ClassLiteral(self, p_node):
    # type: (PNode) -> List[class_literal_term_t]
    """
    class_literal: '[' class_literal_term+ ']'
    """
    assert p_node.typ == grammar_nt.class_literal
    # skip [ and ]
    terms = [self._ClassLiteralTerm(c) for c in p_node.children[1:-1]]
    return terms

  def _NameInRegex(self, negated_tok, tok):
    # type: (Token, Token) -> re_t
    tok_str = tok.tval
    if tok_str == 'dot':
      if negated_tok:
        p_die("Can't negate this symbol", tok)
      return tok

    if tok_str in POSIX_CLASSES:
      return posix_class(negated_tok, tok_str)

    perl = PERL_CLASSES.get(tok_str)
    if perl is not None:
      return perl_class(negated_tok, perl)

    if tok_str[0].isupper():  # e.g. HexDigit
      return re.Splice(tok, lexer.TokenSliceLeft(tok, 1))

    p_die("%r isn't a character class" % tok_str, tok)

  def _NameInClass(self, negated_tok, tok):
    # type: (Token, Token) -> class_literal_term_t
    """
    Like the above, but 'dot' doesn't mean anything.  And `d` is a literal 'd',
    not `digit`.
    """
    tok_str = tok.tval

    # A bare, unquoted character literal.  In the grammar, this is expressed as
    # range_char without an ending.

    # d is NOT 'digit', it's a literal 'd'!
    if len(tok_str) == 1:
      # Expr_Name matches VAR_NAME_RE, which starts with [a-zA-Z_]
      assert tok.id in (Id.Expr_Name, Id.Expr_DecInt)

      if negated_tok:  # [~d] is not allowed, only [~digit]
        p_die("Can't negate this symbol", tok)
      return class_literal_term.CharLiteral(tok)

    # digit, word, but not d, w, etc.
    if tok_str in POSIX_CLASSES:
      return posix_class(negated_tok, tok_str)

    perl = PERL_CLASSES.get(tok_str)
    if perl is not None:
      return perl_class(negated_tok, perl)
    p_die("%r isn't a character class" % tok_str, tok)

  def _ReAtom(self, p_atom):
    # type: (PNode) -> re_t
    """
    re_atom: (
        char_literal
    """
    assert p_atom.typ == grammar_nt.re_atom, p_atom.typ

    children = p_atom.children
    typ = children[0].typ

    if ISNONTERMINAL(typ):
      p_child = p_atom.children[0]
      if typ == grammar_nt.class_literal:
        return re.CharClassLiteral(False, self._ClassLiteral(p_child))

      if typ == grammar_nt.braced_var_sub:
        return cast(braced_var_sub, p_child.children[1].tok)

      if typ == grammar_nt.dq_string:
        return cast(double_quoted, p_child.children[1].tok)

      if typ == grammar_nt.sq_string:
        return cast(single_quoted, p_child.children[1].tok)

      if typ == grammar_nt.simple_var_sub:
        tok = children[0].tok
        return simple_var_sub(tok, lexer.TokenSliceLeft(tok, 1))

      if typ == grammar_nt.char_literal:
        return children[0].tok

      raise NotImplementedError(typ)

    else:
      tok = children[0].tok

      # Special punctuation
      if tok.id in (Id.Expr_Dot, Id.Arith_Caret, Id.Expr_Dollar):
        return tok

      # TODO: d digit can turn into PosixClass and PerlClass right here!
      # It's parsing.
      if tok.id == Id.Expr_Name:
        return self._NameInRegex(None, tok)

      if tok.id == Id.Expr_Symbol:
        # Validate symbols here, like we validate PerlClass, etc.
        if tok.tval in ('%start', '%end', 'dot'):
          return tok
        p_die("Unexpected token %r in regex" % tok.tval, tok)

      if tok.id == Id.Expr_At:
        # | '@' Expr_Name
        tok = children[1].tok
        return re.Splice(tok, lexer.TokenSliceLeft(tok, 1))

      if tok.id == Id.Expr_Bang:
        # | '!' (Expr_Name | class_literal)
        # | '!' '!' Expr_Name (Expr_Name | Expr_DecInt | '(' regex ')')
        n = len(children)
        if n == 2:
          typ = children[1].typ
          if ISNONTERMINAL(typ):
            return re.CharClassLiteral(True, self._ClassLiteral(children[1]))
          else:
            return self._NameInRegex(tok, children[1].tok)
        else:
          # Note: !! conflicts with shell history
          p_die("Backtracking with !! isn't implemented (requires Python/PCRE)",
                children[1].tok)

      if tok.id == Id.Op_LParen:
        # | '(' regex ')'

        # Note: in ERE (d+) is the same as <d+>.  That is, Group becomes
        # Capture.
        return re.Group(self._Regex(children[1]))

      if tok.id == Id.Arith_Less:
        # | '<' regex [':' name_type] '>'

        regex = self._Regex(children[1])

        n = len(children)
        if n == 5:
          # TODO: Add type expression
          # YES
          #   < d+ '.' d+ : ratio Float >
          #   < d+ : month Int >
          # INVALID
          #   < d+ : month List[int] >
          name_tok = children[3].children[0].tok

          # TODO: is it possible to output the capture name <-> index mapping
          # here for POSIX ERE?

        else:
          name_tok = None

        return re.Capture(regex, name_tok)

      if tok.id == Id.Arith_Colon:
        # | ':' '(' regex ')'
        raise NotImplementedError(Id_str(tok.id))

      raise NotImplementedError(Id_str(tok.id))

  def _RepeatOp(self, p_repeat):
    # type: (PNode) -> re_repeat_t
    assert p_repeat.typ == grammar_nt.repeat_op, p_repeat

    tok = p_repeat.children[0].tok
    id_ = tok.id
    # a+
    if id_ in (Id.Arith_Plus, Id.Arith_Star, Id.Arith_QMark):
      return re_repeat.Op(tok)

    if id_ == Id.Op_LBrace:
      p_range = p_repeat.children[1]
      assert p_range.typ == grammar_nt.repeat_range, p_range

      # repeat_range: (
      #     Expr_DecInt [',']
      #   | ',' Expr_DecInt
      #   | Expr_DecInt ',' Expr_DecInt
      # )

      children = p_range.children
      n = len(children)
      if n == 1:  # {3}
        return re_repeat.Num(children[0].tok)

      if n == 2:
        if children[0].tok.id == Id.Expr_DecInt:  # {,3}
          return re_repeat.Range(children[0].tok, None)
        else:  # {1,}
          return re_repeat.Range(None, children[1].tok)

      if n == 3:  # {1,3}
        return re_repeat.Range(children[0].tok, children[2].tok)

      raise AssertionError(n)

    raise AssertionError(id_)

  def _Regex(self, p_node):
    # type: (PNode) -> re_t
    typ = p_node.typ
    children = p_node.children

    if typ == grammar_nt.regex:
      # regex: [re_alt] (('|'|'or') re_alt)*

      if len(children) == 1:
        return self._Regex(children[0])

      # NOTE: We're losing the | and or operators
      alts = []  # type: List[re_t]
      n = len(p_node.children)
      for i in xrange(0, n, 2):  # was children[::2]
        c = p_node.children[i]
        alts.append(self._Regex(c))
      return re.Alt(alts)

    if typ == grammar_nt.re_alt:
      # re_alt: (re_atom [repeat_op])+
      i = 0
      n = len(children)
      seq = []  # type: List[re_t]
      while i < n:
        r = self._ReAtom(children[i])
        i += 1
        if i < n and children[i].typ == grammar_nt.repeat_op:
          repeat_op = self._RepeatOp(children[i])
          r = re.Repeat(r, repeat_op)
          i += 1
        seq.append(r)

      if len(seq) == 1:
        return seq[0]
      else:
        return re.Seq(seq)

    nt_name = self.number2symbol[typ]
    raise NotImplementedError(nt_name)

