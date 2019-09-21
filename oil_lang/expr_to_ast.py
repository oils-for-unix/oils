"""
expr_to_ast.py
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import (
    token, speck, double_quoted, single_quoted, simple_var_sub, braced_var_sub,
    command_sub,
    sh_array_literal,
    command, command__VarDecl,
    expr, expr_t, expr__Dict, expr_context_e,
    re, re_t, re_repeat, re_repeat_t, class_literal_term, class_literal_term_t,
    posix_class, perl_class,
    word_t,
    param, type_expr_t, comprehension,
)
from _devbuild.gen import grammar_nt
from pgen2.parse import PNode
from core.util import log, p_die

from typing import TYPE_CHECKING, List, Tuple, Optional, cast
if TYPE_CHECKING:
  from pgen2.grammar import Grammar

unused1 = word_t  # shut up lint, it's used below
unused2 = log


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
    left, op = self.Expr(children[0]), children[1]
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

    if op_tok.id in (Id.Expr_Dot, Id.Expr_RArrow, Id.Expr_DColon):
      attr = children[1].tok  # will be Id.Expr_Name
      return expr.Attribute(base, op_tok, attr, expr_context_e.Store)

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

  RANGE_POINT_TOO_LONG = "Range start/end shouldn't have more than one character"

  def _RangeChar(self, p_node):
    # type: (PNode) -> str
    """
    the 'a' in 'a'-'z'
    the \x00 in \x00-\x01
    etc.
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
          p_die(self.RANGE_POINT_TOO_LONG, part=sq_part)
        if len(tokens[0].val) > 1:
          p_die(self.RANGE_POINT_TOO_LONG, part=sq_part)
        s = tokens[0].val[0]
        return s

      raise NotImplementedError
    else:
      # Expr_Name or Expr_DecInt
      tok = p_node.tok
      #
      if tok.id in (Id.Expr_Name, Id.Expr_DecInt):
        # For the a in a-z, 0 in 0-9
        if len(tok.val) != 1:
          p_die(self.RANGE_POINT_TOO_LONG, token=tok)
        return tok.val[0]

      # TODO: \n \' are valid in ranges
      raise NotImplementedError

  def _NonRangeChars(self, p_node):
    # type: (PNode) -> class_literal_term_t
    """
    \" \u123 '#'
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
        return simple_var_sub(children[0].tok)

      raise NotImplementedError
    else:
      # Look up PerlClass and PosixClass
      return self._NameInClass(False, children[0].tok)

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
      n = len(children)

      if n == 1 and children[0].typ == grammar_nt.range_char:
        return self._NonRangeChars(children[0])

      if n == 3 and children[1].tok.id == Id.Arith_Minus:
        start = self._RangeChar(children[0])
        end = self._RangeChar(children[2])
        return class_literal_term.Range(start, end)

    else:
      if children[0].tok.id == Id.Arith_Tilde:
        return self._NameInClass(True, children[1].tok)

    typ = p_node.children[0].typ
    nt_name = self.number2symbol[typ]
    raise NotImplementedError(nt_name)

  def _ClassLiteral(self, p_node):
    # type: (PNode) -> List[class_literal_term_t]
    """
    class_literal: '[' class_literal_term+ ']'
    """
    assert p_node.typ == grammar_nt.class_literal
    # skip [ and ]
    return [self._ClassLiteralTerm(c) for c in p_node.children[1:-1]]

  PERL_CLASSES = {
      'd': 'd',
      'w': 'w', 'word': 'w',
      's': 's',
  }
  # https://pubs.opengroup.org/onlinepubs/9699919799/basedefs/V1_chap09.html
  POSIX_CLASSES = (
      'alnum', 'cntrl', 'lower', 'space',
      'alpha', 'digit', 'print', 'upper',
      'blank', 'graph', 'punct', 'xdigit',
  )

  def _NameInRegex(self, negated, tok):
    # type: (bool, token) -> re_t
    val = tok.val
    if val == 'dot':
      if negated:
        p_die("Can't negate this symbol", token=tok)
      return tok

    if val in self.POSIX_CLASSES:
      return posix_class(negated, val)

    perl = self.PERL_CLASSES.get(val)
    if perl:
      return perl_class(negated, perl)
    p_die("%r isn't a character class", val, token=tok)

  def _NameInClass(self, negated, tok):
    # type: (bool, token) -> class_literal_term_t
    """
    Like the above, but 'dot' doesn't mean anything.
    """
    val = tok.val
    if val in self.POSIX_CLASSES:
      return posix_class(negated, val)

    perl = self.PERL_CLASSES.get(val)
    if perl:
      return perl_class(negated, perl)
    p_die("%r isn't a character class", val, token=tok)

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
        return re.ClassLiteral(False, self._ClassLiteral(p_child))

      if typ == grammar_nt.braced_var_sub:
        return cast(braced_var_sub, p_child.children[1].tok)

      if typ == grammar_nt.dq_string:
        return cast(double_quoted, p_child.children[1].tok)

      if typ == grammar_nt.sq_string:
        return cast(single_quoted, p_child.children[1].tok)

      if typ == grammar_nt.simple_var_sub:
        return simple_var_sub(children[0].tok)

      raise NotImplementedError(typ)

    else:
      tok = children[0].tok

      # Special punctuation
      if tok.id in (Id.Expr_Dot, Id.Arith_Caret, Id.Expr_Dollar):
        return speck(tok.id, tok.span_id)

      # TODO: d digit can turn into PosixClass and PerlClass right here!
      # It's parsing.
      if tok.id == Id.Expr_Name:
        return self._NameInRegex(False, tok)

      if tok.id == Id.Expr_Symbol:
        # Validate symbols here, like we validate PerlClass, etc.
        if tok.val in ('%start', '%end', 'dot'):
          return tok
        p_die("Unexpected token %r in regex", tok.val, token=tok)

      if tok.id == Id.Expr_At:
        # | '@' Expr_Name
        return re.Splice(children[1].tok)

      if tok.id == Id.Arith_Tilde:
        # | '~' [Expr_Name | class_literal]
        typ = children[1].typ
        if ISNONTERMINAL(typ):
          ch = children[1].children
          return re.ClassLiteral(True, self._ClassLiteral(children[1]))
        else:
          return self._NameInRegex(True, children[1].tok)

      if tok.id == Id.Op_LParen:
        # | '(' regex ['as' name_type] ')'

        # TODO: Add variable
        return re.Group(self._Regex(children[1]))

      if tok.id == Id.Arith_Colon:
        # | ':' '(' regex ')'
        raise NotImplementedError(tok.id)

      raise NotImplementedError(tok.id)

  def _RepeatOp(self, p_repeat):
    # type: (PNode) -> re_repeat_t
    tok = p_repeat.children[0].tok
    id_ = tok.id
    # a+
    if id_ in (Id.Arith_Plus, Id.Arith_Star, Id.Arith_QMark):
      return re_repeat.Op(tok)

    if id_ == Id.Arith_Caret:
      raise NotImplementedError(id_)

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
      children = p_node.children[0::2]
      return re.Alt([self._Regex(c) for c in children])

    if typ == grammar_nt.re_alt:
      # re_alt: (re_atom [repeat_op])+
      i = 0
      n = len(children)
      seq = []
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

    if id_ == Id.Arith_Slash:
      r = self._Regex(children[1])
      flags = []  # type: List[token]
      return expr.RegexLiteral(children[0].tok, r, flags)

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

      #
      # Oil Entry Points / Additions
      #

      if typ == grammar_nt.oil_expr:  # for if/while
        # oil_expr: '(' testlist ')'
        return self.Expr(children[1])

      if typ == grammar_nt.return_expr:
        # return_expr: testlist end_stmt
        return self.Expr(children[0])

      if typ == grammar_nt.place_list:
        return self._AssocBinary(children)

      if typ == grammar_nt.place:
        # place: NAME place_trailer*
        if len(pnode.children) == 1:
          return self.Expr(pnode.children[0])
        # TODO: Called _Trailer but don't handle ( )?
        # only [] . -> :: ?
        raise NotImplementedError

      #
      # Python-like Expressions / Operators
      #

      if typ == grammar_nt.atom:
        if len(children) == 1:
          return self.Expr(children[0])
        return self._Atom(children)

      if typ == grammar_nt.testlist:
        # testlist: test (',' test)* [',']
        # We need tuples for Python's 'var a, b = x' and 'for (a, b in x) {'
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

      if typ == grammar_nt.test_nocond:
        # test_nocond: or_test | lambdef_nocond
        assert len(children) == 1
        return self.Expr(children[0])

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

        op_tok = children[0].tok
        #log('op_tok %s', op_tok)
        return expr.Unary(op_tok, self.Expr(children[1]))


      elif typ == grammar_nt.comparison:
        # comparison: expr (comp_op expr)*
        return self._AssocBinary(children)

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
        op, e = children
        assert isinstance(op.tok, token)
        return expr.Unary(op.tok, self.Expr(e))

      elif typ == grammar_nt.power:
        # power: atom trailer* ['^' factor]

        node = self.Expr(children[0])
        if len(children) == 1:  # No trailers
          return node

        n = len(children)
        i = 1
        while i < n and ISNONTERMINAL(children[i].typ):
          node = self._Trailer(node, children[i])
          i += 1

        if i != n:  # ['^' factor]
          op_tok = children[i].tok
          assert op_tok.id == Id.Arith_Caret, op_tok
          factor = self.Expr(children[i+1])
          node = expr.Binary(op_tok, node, factor)

        return node

      #
      # Oil Lexer Modes
      #

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

        # HACK: When typ is Id.Expr_CastedDummy, the 'tok' field ('opaque')
        # actually has a list of words!
        typ1 = children[1].typ
        assert typ1 == Id.Expr_CastedDummy.enum_id, typ1
        array_words = cast('List[word_t]', children[1].tok)

        return sh_array_literal(left_tok, array_words)

      elif typ == grammar_nt.sh_command_sub:
        return cast(command_sub, children[1].tok)

      elif typ == grammar_nt.braced_var_sub:
        return cast(braced_var_sub, children[1].tok)

      elif typ == grammar_nt.dq_string:
        return cast(double_quoted, children[1].tok)

      elif typ == grammar_nt.sq_string:
        return cast(single_quoted, children[1].tok)

      elif typ == grammar_nt.simple_var_sub:
        return simple_var_sub(children[0].tok)

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
