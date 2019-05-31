#!/usr/bin/python
"""
expr_to_ast.py
"""
from __future__ import print_function


from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen import syntax_asdl
from _devbuild.gen.syntax_asdl import (
    command, oil_expr, oil_word_part, regex
)


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
    return oil_expr.Binary(op.tok, self.Transform(left), right)

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
       return oil_expr.FuncCall(base, [self.Transform(a) for a in arglist])

    if op_tok.id == Id.Op_LBracket:
       p_args = children[1]

       # NOTE: This doens't take into account slices
       if p_args.children is not None:
         # a, b, c -- every other one is a comma
         arglist = children[1].children[::2]
       else:
         arg = children[1]
         arglist = [arg]
       return oil_expr.Subscript(base, [self.Transform(a) for a in arglist])

    if op_tok.id == Id.Expr_Dot:
      #return self._GetAttr(base, nodelist[2])
      raise NotImplementedError

    raise AssertionError(op_tok)

  def Transform(self, pnode):
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

      if nt_name == 'test_input':
        # test_input: test NEWLINE* ENDMARKER
        return self.Transform(children[0])

      elif nt_name == 'expr':
        # expr: term (('+'|'-') term)*
        return self._AssocBinary(children)

      elif nt_name == 'term':
        # term: factor (('*'|'/'|'div'|'mod') factor)*
        return self._AssocBinary(children)

      elif nt_name == 'factor':
        # factor: ('+'|'-'|'~') factor | power
        # the power would have already been reduced
        assert len(children) == 2, children
        op, e = children
        assert isinstance(op.tok, syntax_asdl.token)
        return oil_expr.Unary(op.tok, self.Transform(e))

      elif nt_name == 'power':
        # power: atom trailer* ['^' factor]

        # atom is already reduced to a token

        # NOTE: This would be shorter in a recursive style.

        base = self.Transform(children[0])
        n = len(children)
        for i in xrange(1, n):
          pnode = children[i]
          tok = pnode.tok
          if tok and tok.id == Id.Arith_Caret:
            return oil_expr.Binary(tok, base, self.Transform(children[i+1]))
          base = self._Trailer(base, pnode)

        return base

      elif nt_name == 'array_literal':
        left_tok = children[0].tok

        # Approximation for now.
        items = [
            pnode.tok for pnode in children[1:-1] if pnode.tok.id ==
            Id.Lit_Chars
        ]

        return oil_expr.ArrayLiteral(left_tok, items)

      elif nt_name == 'regex_literal':
        left_tok = children[0].tok

        # Approximation for now.
        items = [
            pnode.tok for pnode in children[1:-1] if pnode.tok.id ==
            Id.Expr_Name
        ]

        return oil_expr.RegexLiteral(left_tok, regex.Concat(items))

      elif nt_name == 'command_sub':
        left_tok = children[0].tok

        # Approximation for now.
        items = [
            pnode.tok for pnode in children[1:-1] if pnode.tok.id ==
            Id.Lit_Chars
        ]

        # TODO: Fix this approximation.
        words = items
        return oil_expr.CommandSub(left_tok, command.SimpleCommand(words))

      elif nt_name == 'expr_sub':
        left_tok = children[0].tok

        return oil_expr.ExprSub(left_tok, self.Transform(children[1]))

      elif nt_name == 'var_sub':
        left_tok = children[0].tok

        return oil_expr.VarSub(left_tok, self.Transform(children[1]))

      elif nt_name == 'dq_string':
        left_tok = children[0].tok

        parts = [self.Transform(c) for c in children[1:-1]]
        return oil_expr.DoubleQuoted(left_tok, parts)

      else:
        raise AssertionError(nt_name)

    else:  # Terminals should have a token
      #log('terminal %s', tok)

      if tok.id == Id.Expr_Name:
        return oil_expr.Var(tok)
      elif tok.id == Id.Expr_Digits:
        return oil_expr.Const(tok)

      # Hm just use word_part.Literal for all these?  Or token?
      # Id.Lit_EscapedChar is assumed to need \ removed on evaluation.
      elif tok.id in (Id.Lit_Chars, Id.Lit_Other, Id.Lit_EscapedChar):
        return oil_word_part.Literal(tok)
      else:
        raise AssertionError(tok.id)

