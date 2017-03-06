#!/usr/bin/env python3
"""
arith_parse.py - Parse shell arithmetic, which is based on C.
"""

import sys

from core import tdop
from core.id_kind import Id
from core import word
from osh import ast_ as ast


def NullIncDec(p, w, bp):
  """ ++x or ++x[1] """
  right = p.ParseUntil(bp)
  if not tdop.IsLValue(right):
    raise tdop.ParseError("Can't assign to %r (%s)" % (right, right.token))
  return ast.ArithUnary(word.ArithId(w), right)


def NullUnaryPlus(p, t, bp):
  """ +x, to distinguish from binary operator. """
  right = p.ParseUntil(bp)
  return ast.ArithUnary(Id.Node_UnaryPlus, right)


def NullUnaryMinus(p, t, bp):
  """ -1, to distinguish from binary operator. """
  right = p.ParseUntil(bp)
  return ast.ArithUnary(Id.Node_UnaryMinus, right)


def LeftIncDec(p, w, left, rbp):
  """ For i++ and i--
  """
  if not tdop.IsLValue(left):
    raise tdop.ParseError("Can't assign to %r (%s)" % (left, left.token))
  if word.ArithId(w) == Id.Arith_DPlus:
    op_id = Id.Node_PostDPlus
  elif word.ArithId(w) == Id.Arith_DMinus:
    op_id = Id.Node_PostDMinus
  else:
    raise AssertionError
  return ast.ArithUnary(op_id, left)


def LeftIndex(p, w, left, unused_bp):
  """ index f[x+1] """
  # f[x] or f[x][y]
  if not tdop.IsIndexable(left):
    raise tdop.ParseError("%s can't be indexed" % left)
  index = p.ParseUntil(0)
  p.Eat(Id.Arith_RBracket)

  return ast.ArithBinary(word.ArithId(w), left, index)


def LeftTernary(p, t, left, bp):
  """ Function call f(a, b). """
  true_expr = p.ParseUntil(bp)
  p.Eat(Id.Arith_Colon)
  false_expr = p.ParseUntil(bp)
  return ast.TernaryOp(left, true_expr, false_expr)


# For overloading of , inside function calls
COMMA_PREC = 1

def LeftFuncCall(p, t, left, unused_bp):
  """ Function call f(a, b). """
  children = []
  # f(x) or f[i](x)
  if not tdop.IsCallable(left):
    raise tdop.ParseError("%s can't be called" % left)
  while not p.AtToken(Id.Arith_RParen):
    # We don't want to grab the comma, e.g. it is NOT a sequence operator.  So
    # set the precedence to 5.
    children.append(p.ParseUntil(COMMA_PREC))
    if p.AtToken(Id.Arith_Comma):
      p.Next()
  p.Eat(Id.Arith_RParen)
  return ast.FuncCall(left, children)


def MakeShellSpec():
  """
  Following this table:
  http://en.cppreference.com/w/c/language/operator_precedence

  Bash has a table in expr.c, but it's not as cmoplete (missing grouping () and
  array[1]).  Although it has the ** exponentation operator, not in C.

  - Extensions:
    - function calls f(a,b)

  - Possible extensions (but save it for oil):
    - could allow attribute/object access: obj.member and obj.method(x)
    - could allow extended indexing: t[x,y] -- IN PLACE OF COMMA operator.
      - also obj['member'] because dictionaries are objects
  """
  spec = tdop.ParserSpec()

  # -1 precedence -- doesn't matter
  spec.Null(-1, tdop.NullConstant, [
      Id.Word_Compound,
      Id.Arith_Semi,  # for loop
  ])
  spec.Null(-1, tdop.NullError, [
      Id.Arith_RParen, Id.Arith_RBracket, Id.Arith_Colon,
      Id.Eof_Real, Id.Eof_RParen, Id.Eof_Backtick,
      # Not in the arithmetic language, but is a common terminator, e.g.
      # ${foo:1}
      Id.Arith_RBrace,
  ])

  # 0 precedence -- doesn't bind until )
  spec.Null(0, tdop.NullParen, [Id.Arith_LParen])  # for grouping

  spec.Left(33, LeftIncDec, [Id.Arith_DPlus, Id.Arith_DMinus])
  spec.Left(33, LeftFuncCall, [Id.Arith_LParen])
  spec.Left(33, LeftIndex, [Id.Arith_LBracket])

  # 31 -- binds to everything except function call, indexing, postfix ops
  spec.Null(31, NullIncDec, [Id.Arith_DPlus, Id.Arith_DMinus])
  spec.Null(31, NullUnaryPlus, [Id.Arith_Plus])
  spec.Null(31, NullUnaryMinus, [Id.Arith_Minus])
  spec.Null(31, tdop.NullPrefixOp, [Id.Arith_Bang, Id.Arith_Tilde])

  # Right associative: 2 ** 3 ** 2 == 2 ** (3 ** 2)
  # NOTE: This isn't in C
  spec.LeftRightAssoc(29, tdop.LeftBinaryOp, [Id.Arith_DStar])

  # * / %
  spec.Left(27, tdop.LeftBinaryOp, [
      Id.Arith_Star, Id.Arith_Slash, Id.Arith_Percent])

  spec.Left(25, tdop.LeftBinaryOp, [Id.Arith_Plus, Id.Arith_Minus])
  spec.Left(23, tdop.LeftBinaryOp, [Id.Arith_DLess, Id.Arith_DGreat])
  spec.Left(21, tdop.LeftBinaryOp, [
      Id.Arith_Less, Id.Arith_Great, Id.Arith_LessEqual, Id.Arith_GreatEqual])

  spec.Left(19, tdop.LeftBinaryOp, [Id.Arith_NEqual, Id.Arith_DEqual])

  spec.Left(15, tdop.LeftBinaryOp, [Id.Arith_Amp])
  spec.Left(13, tdop.LeftBinaryOp, [Id.Arith_Caret])
  spec.Left(11, tdop.LeftBinaryOp, [Id.Arith_Pipe])
  spec.Left(9, tdop.LeftBinaryOp, [Id.Arith_DAmp])
  spec.Left(7, tdop.LeftBinaryOp, [Id.Arith_DPipe])

  spec.Left(5, LeftTernary, [Id.Arith_QMark])

  # Right associative: a = b = 2 is a = (b = 2)
  spec.LeftRightAssoc(3, tdop.LeftAssign, [
      Id.Arith_Equal,
      Id.Arith_PlusEqual, Id.Arith_MinusEqual, Id.Arith_StarEqual,
      Id.Arith_SlashEqual, Id.Arith_PercentEqual, Id.Arith_DLessEqual,
      Id.Arith_DGreatEqual, Id.Arith_AmpEqual, Id.Arith_CaretEqual,
      Id.Arith_PipeEqual
  ])

  spec.Left(COMMA_PREC, tdop.LeftBinaryOp, [Id.Arith_Comma])

  return spec


SPEC = MakeShellSpec()
