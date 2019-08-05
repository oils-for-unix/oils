"""
expr_to_ast.py
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen import syntax_asdl
from _devbuild.gen.syntax_asdl import (
    command, command__OilAssign,
    expr, expr_t, expr_context_e, regex, regex_t, word, word_t, word_part,
    oil_word_part, oil_word_part_t,
)
from _devbuild.gen import grammar_nt
from pgen2.parse import PNode
#from core.util import log

from typing import TYPE_CHECKING, List, cast
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
    Expr, OilAssign
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
    assert len(children) >= 3, children
    # Note: Compare the iteractive com_binary() method in
    # opy/compiler2/transformer.py.

    left, op = children[0], children[1]
    if len(children) == 3:
      right = self.Expr(children[2])
    else:
      right = self._AssocBinary(children[2:])

    assert isinstance(op.tok, syntax_asdl.token)
    return expr.Binary(op.tok, self.Expr(left), right)

  def trailer(self, base, p_trailer):
    # type: (expr_t, PNode) -> expr_t
    children = p_trailer.children
    op_tok = children[0].tok

    if op_tok.id == Id.Op_LParen:
       p_args = children[1]

       # NOTE: This doesn't take into account kwargs and so forth.
       if p_args.children is not None:
         # a, b, c -- every other one is a comma
         arglist = children[1].children[::2]
       else:
         arg = children[1]
         arglist = [arg]
       return expr.FuncCall(base, [self.Expr(a) for a in arglist])

    if op_tok.id == Id.Op_LBracket:
       p_args = children[1]

       # NOTE: This doens't take into account slices
       if p_args.children is not None:
         # a, b, c -- every other one is a comma
         arglist = children[1].children[::2]
       else:
         arg = children[1]
         arglist = [arg]
       return expr.Subscript(base, [self.Expr(a) for a in arglist])

    if op_tok.id == Id.Expr_Dot:
      #return self._GetAttr(base, nodelist[2])
      raise NotImplementedError

    raise AssertionError(op_tok)

  def atom(self, children):
    # type: (List[PNode]) -> expr_t
    """Handles alternatives of 'atom' where there is more than one child."""

    id_ = children[0].tok.id

    if id_ == Id.Op_LParen:
      # atom: '(' [yield_expr|testlist_comp] ')' | ...
      return self.Expr(children[1])

    if id_ == Id.Op_LBracket:
      # atom: ... | '[' [testlist_comp] ']' | ...

      if len(children) == 2:  # []
        return expr.List([], expr_context_e.Store)  # unused expr_context_e

      p_list = children[1].children  # what's between [ and ]

      # [x for x in y]
      if len(p_list) == 2 and p_list[1].typ == grammar_nt.sync_comp_for:
        elt = self.Expr(p_list[0])

        # TODO: transform 'for', 'if', etc.
        return expr.ListComp(elt, [])

      # [1, 2, 3]
      n = len(p_list)
      elts = []
      for i in xrange(0, n, 2):  # skip commas
        p_node = p_list[i]
        elts.append(self.Expr(p_node))

      return expr.List(elts, expr_context_e.Store)  # unused expr_context_e

    raise NotImplementedError

  def Expr(self, pnode):
    # type: (PNode) -> expr_t
    """Transform expressions (as opposed to statements)."""
    typ = pnode.typ
    tok = pnode.tok
    children = pnode.children

    #if typ in self.number2symbol:  # non-terminal
    if ISNONTERMINAL(typ):
      c = '-' if not children else len(children)
      #log('non-terminal %s %s', nt_name, c)

      if typ == grammar_nt.lvalue_list:
        return self._AssocBinary(children)

      if typ == grammar_nt.atom:
        return self.atom(children)

      if typ == grammar_nt.eval_input:
        # testlist_input: testlist NEWLINE* ENDMARKER
        return self.Expr(children[0])

      if typ == grammar_nt.testlist:
        # testlist: test (',' test)* [',']
        return self._AssocBinary(children)

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
        assert len(children) == 2, children
        op, e = children
        assert isinstance(op.tok, syntax_asdl.token)
        return expr.Unary(op.tok, self.Expr(e))

      elif typ == grammar_nt.atom_expr:
        # atom_expr: ['await'] atom trailer*

        # NOTE: This would be shorter in a recursive style.
        base = self.Expr(children[0])
        n = len(children)
        for i in xrange(1, n):
          pnode = children[i]
          tok = pnode.tok
          base = self.trailer(base, pnode)

        return base

      elif typ == grammar_nt.power:
        # power: atom_expr ['^' factor]

        # This doesn't repeat, so it doesn't matter if it's left or right
        # associative.
        return self._AssocBinary(children)

      elif typ == grammar_nt.array_literal:
        left_tok = children[0].tok

        # Approximation for now.
        tokens = [
            pnode.tok for pnode in children[1:-1] if pnode.tok.id ==
            Id.Lit_Chars
        ]
        array_words = [
            word.CompoundWord([word_part.LiteralPart(t)]) for t in tokens
        ]  # type: List[word_t]
        return expr.ArrayLiteral(left_tok, array_words)

      elif typ == grammar_nt.sh_array_literal:
        left_tok = children[0].tok

        # HACK: When typ is Id.Expr_WordsDummy, the 'tok' field ('opaque')
        # actually has a list of words!
        typ1 = children[1].typ
        assert typ1 == Id.Expr_WordsDummy.enum_id, typ1
        array_words = cast('List[word_t]', children[1].tok)

        return expr.ArrayLiteral(left_tok, array_words)

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
            word.CompoundWord([word_part.LiteralPart(t)]) for t in tokens
        ]  # type: List[word_t]
        return expr.CommandSub(left_tok, command.SimpleCommand(words))

      elif typ == grammar_nt.expr_sub:
        left_tok = children[0].tok

        return expr.ExprSub(left_tok, self.Expr(children[1]))

      elif typ == grammar_nt.var_sub:
        left_tok = children[0].tok

        return expr.VarSub(left_tok, self.Expr(children[1]))

      elif typ == grammar_nt.dq_string:
        left_tok = children[0].tok

        tokens = [
            pnode.tok for pnode in children[1:-1] if pnode.tok.id ==
            Id.Lit_Chars
        ]
        parts2 = [
            oil_word_part.Literal(t) for t in tokens
        ]  # type: List[oil_word_part_t]
        return expr.DoubleQuoted(left_tok, parts2)

      else:
        nt_name = self.number2symbol[typ]
        raise AssertionError(
            "PNode type %d (%s) wasn't handled" % (typ, nt_name))

    else:  # Terminals should have a token
      #log('terminal %s', tok)

      if tok.id == Id.Expr_Name:
        return expr.Var(tok)
      elif tok.id == Id.Expr_Digits:
        return expr.Const(tok)

      else:
        raise AssertionError(tok.id)

  def OilAssign(self, pnode):
    # type: (PNode) -> command__OilAssign
    """Transform an Oil assignment statement."""
    typ = pnode.typ
    children = pnode.children

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
      # TODO: type expression
      return command.OilAssign(None, lvalue, op_tok, self.Expr(rhs))

    if typ == grammar_nt.oil_setvar:
      # oil_setvar: lvalue_list (augassign | '=') testlist (Op_Semi | Op_Newline)
      lvalue = self.Expr(children[0])  # could be a tuple
      op_tok = children[1].tok
      rhs = children[2]
      return command.OilAssign(None, lvalue, op_tok, self.Expr(rhs))

    nt_name = self.number2symbol[typ]
    raise AssertionError(
        "PNode type %d (%s) wasn't handled" % (typ, nt_name))
