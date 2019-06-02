#!/usr/bin/python
"""
expr_to_ast.py
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen import syntax_asdl
from _devbuild.gen.syntax_asdl import (
    command, expr, expr_t, oil_word_part, regex
)

from core.util import log

from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from pgen2.parse import PNode

# TODO: We need a _devbuild/gen/nonterm.py file generated from grammar.pgen2.
# Instead of all the string comparisons.

class Transformer(object):
  
  def __init__(self, gr):
    self.number2symbol = gr.number2symbol

  def _AssocBinary(self, children):
    """For an associative binary operation.

    We don't care if it's (1+2)+3 or 1+(2+3).
    """
    assert len(children) >= 3, children
    # NOTE: opy/compiler2/transformer.py has an interative version of this in
    # com_binary.

    left, op = children[0], children[1]
    if len(children) == 3:
      right = self.Transform(children[2])
    else:
      right = self._AssocBinary(children[2:])

    assert isinstance(op.tok, syntax_asdl.token)
    return expr.Binary(op.tok, self.Transform(left), right)

  def _Trailer(self, base, p_trailer):
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
       return expr.FuncCall(base, [self.Transform(a) for a in arglist])

    if op_tok.id == Id.Op_LBracket:
       p_args = children[1]

       # NOTE: This doens't take into account slices
       if p_args.children is not None:
         # a, b, c -- every other one is a comma
         arglist = children[1].children[::2]
       else:
         arg = children[1]
         arglist = [arg]
       return expr.Subscript(base, [self.Transform(a) for a in arglist])

    if op_tok.id == Id.Expr_Dot:
      #return self._GetAttr(base, nodelist[2])
      raise NotImplementedError

    raise AssertionError(op_tok)

  def Transform(self, pnode):
    # type: (PNode) -> expr_t
    """Walk the homogeneous parse tree and create a typed AST."""
    typ = pnode.typ
    if pnode.tok:
      value = pnode.tok.val
    else:
      value = None
    tok = pnode.tok
    children = pnode.children

    if typ in self.number2symbol:  # non-terminal
      nt_name = self.number2symbol[typ]

      c = '-' if not children else len(children)
      #log('non-terminal %s %s', nt_name, c)

      if nt_name == 'assign':
        # assign: lvalue_list type_expr? (augassign | '=') testlist
        lvalue = self.Transform(children[0])  # could be a tuple
        log('lvalue %s', lvalue)
        op = children[1].tok
        log('op %s', op)
        rhs = self.Transform(children[2])
        # The caller should fill in the keyword token.
        return command.OilAssign(None, lvalue, op, rhs)

      if nt_name == 'lvalue_list':
        return self._AssocBinary(children)

      if nt_name == 'eval_input':
        # testlist_input: testlist NEWLINE* ENDMARKER
        return self.Transform(children[0])

      if nt_name == 'testlist':
        # testlist: test (',' test)* [',']
        return self._AssocBinary(children)

      elif nt_name == 'arith_expr':
        # expr: term (('+'|'-') term)*
        return self._AssocBinary(children)

      elif nt_name == 'term':
        # term: factor (('*'|'/'|'div'|'mod') factor)*
        return self._AssocBinary(children)

      elif nt_name == 'expr':
        # expr: xor_expr ('|' xor_expr)*
        return self._AssocBinary(children)

      elif nt_name == 'shift_expr':
        # shift_expr: arith_expr (('<<'|'>>') arith_expr)*
        return self._AssocBinary(children)

      elif nt_name == 'comparison':
        # comparison: expr (comp_op expr)*
        return self._AssocBinary(children)

      elif nt_name == 'factor':
        # factor: ('+'|'-'|'~') factor | power
        # the power would have already been reduced
        assert len(children) == 2, children
        op, e = children
        assert isinstance(op.tok, syntax_asdl.token)
        return expr.Unary(op.tok, self.Transform(e))

      elif nt_name == 'atom_expr':
        # atom_expr: ['await'] atom trailer*

        # NOTE: This would be shorter in a recursive style.
        base = self.Transform(children[0])
        n = len(children)
        for i in xrange(1, n):
          pnode = children[i]
          tok = pnode.tok
          base = self._Trailer(base, pnode)

        return base

      elif nt_name == 'power':
        # power: atom_expr ['^' factor]

        # This doesn't repeat, so it doesn't matter if it's left or right
        # associative.
        return self._AssocBinary(children)

      elif nt_name == 'array_literal':
        left_tok = children[0].tok

        # Approximation for now.
        items = [
            pnode.tok for pnode in children[1:-1] if pnode.tok.id ==
            Id.Lit_Chars
        ]

        return expr.ArrayLiteral(left_tok, items)

      elif nt_name == 'regex_literal':
        left_tok = children[0].tok

        # Approximation for now.
        items = [
            pnode.tok for pnode in children[1:-1] if pnode.tok.id ==
            Id.Expr_Name
        ]

        return expr.RegexLiteral(left_tok, regex.Concat(items))

      elif nt_name == 'command_sub':
        left_tok = children[0].tok

        # Approximation for now.
        items = [
            pnode.tok for pnode in children[1:-1] if pnode.tok.id ==
            Id.Lit_Chars
        ]

        # TODO: Fix this approximation.
        words = items
        return expr.CommandSub(left_tok, command.SimpleCommand(words))

      elif nt_name == 'expr_sub':
        left_tok = children[0].tok

        return expr.ExprSub(left_tok, self.Transform(children[1]))

      elif nt_name == 'var_sub':
        left_tok = children[0].tok

        return expr.VarSub(left_tok, self.Transform(children[1]))

      elif nt_name == 'dq_string':
        left_tok = children[0].tok

        parts = [self.Transform(c) for c in children[1:-1]]
        return expr.DoubleQuoted(left_tok, parts)

      else:
        raise AssertionError(nt_name)

    else:  # Terminals should have a token
      #log('terminal %s', tok)

      if tok.id == Id.Expr_Name:
        return expr.Var(tok)
      elif tok.id == Id.Expr_Digits:
        return expr.Const(tok)

      # Hm just use word_part.Literal for all these?  Or token?
      # Id.Lit_EscapedChar is assumed to need \ removed on evaluation.
      elif tok.id in (Id.Lit_Chars, Id.Lit_Other, Id.Lit_EscapedChar):
        return oil_word_part.Literal(tok)
      else:
        raise AssertionError(tok.id)

