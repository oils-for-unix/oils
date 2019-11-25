#!/usr/bin/env python2
"""
arith_parse.py - Parse shell arithmetic, which is based on C.
"""

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import (arith_expr, arith_expr_t, word_t)
from core.util import p_die
from osh import tdop
from osh import word_
from mycpp import mylib

from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from osh.tdop import TdopParser, ParserSpec


def NullIncDec(p, w, bp):
  # type: (TdopParser, word_t, int) -> arith_expr_t
  """ ++x or ++x[1] """
  right = p.ParseUntil(bp)
  child = tdop.ToLValue(right)
  if child is None:
    p_die("This value can't be assigned to", word=w)
  return arith_expr.UnaryAssign(word_.ArithId(w), child)


def NullUnaryPlus(p, t, bp):
  # type: (TdopParser, word_t, int) -> arith_expr_t
  """ +x, to distinguish from binary operator. """
  right = p.ParseUntil(bp)
  return arith_expr.Unary(Id.Node_UnaryPlus, right)


def NullUnaryMinus(p, t, bp):
  # type: (TdopParser, word_t, int) -> arith_expr_t
  """ -1, to distinguish from binary operator. """
  right = p.ParseUntil(bp)
  return arith_expr.Unary(Id.Node_UnaryMinus, right)


def LeftIncDec(p, w, left, rbp):
  # type: (TdopParser, word_t, arith_expr_t, int) -> arith_expr_t
  """ For i++ and i--
  """
  if word_.ArithId(w) == Id.Arith_DPlus:
    op_id = Id.Node_PostDPlus
  elif word_.ArithId(w) == Id.Arith_DMinus:
    op_id = Id.Node_PostDMinus
  else:
    raise AssertionError()

  child = tdop.ToLValue(left)
  return arith_expr.UnaryAssign(op_id, child)


def LeftIndex(p, w, left, unused_bp):
  # type: (TdopParser, word_t, arith_expr_t, int) -> arith_expr_t
  """Array indexing, in both LValue and RValue context.

  LValue: f[0] = 1  f[x+1] = 2
  RValue: a = f[0]  b = f[x+1]

  On RHS, you can have:
  1. a = f[0]
  2. a = f(x, y)[0]
  3. a = f[0][0]  # in theory, if we want character indexing?
     NOTE: a = f[0].charAt() is probably better

  On LHS, you can only have:
  1. a[0] = 1

  Nothing else is valid:
  2. function calls return COPIES.  They need a name, at least in osh.
  3. strings don't have mutable characters.
  """
  if not tdop.IsIndexable(left):
    p_die("The [ operarator doesn't apply to this expression", word=w)
  index = p.ParseUntil(0)
  p.Eat(Id.Arith_RBracket)

  return arith_expr.Binary(word_.ArithId(w), left, index)


def LeftTernary(p, t, left, bp):
  # type: (TdopParser, word_t, arith_expr_t, int) -> arith_expr_t
  """ Function call f(a, b). """
  true_expr = p.ParseUntil(bp)
  p.Eat(Id.Arith_Colon)
  false_expr = p.ParseUntil(bp)
  return arith_expr.TernaryOp(left, true_expr, false_expr)


if mylib.PYTHON:
  def MakeShellSpec():
    # type: () -> tdop.ParserSpec
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
    ])
    spec.Null(-1, tdop.NullError, [
        Id.Arith_RParen, Id.Arith_RBracket, Id.Arith_Colon,
        Id.Eof_Real, Id.Eof_RParen, Id.Eof_Backtick,

        # Not in the arithmetic language, but useful to define here.
        Id.Arith_Semi,  # terminates loops like for (( i = 0 ; ... ))
        Id.Arith_RBrace,  # terminates slices like ${foo:1}
    ])

    # 0 precedence -- doesn't bind until )
    spec.Null(0, tdop.NullParen, [Id.Arith_LParen])  # for grouping

    spec.Left(33, LeftIncDec, [Id.Arith_DPlus, Id.Arith_DMinus])
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

    # NOTE: Bitwise & | ^ have lower precedence than comparisons!
    # Python and Rust correct this:
    # https://graydon2.dreamwidth.org/218040.html
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

    spec.Left(1, tdop.LeftBinaryOp, [Id.Arith_Comma])

    return spec


if mylib.PYTHON:
  _SPEC = MakeShellSpec()

  def Spec():
    # type: () -> ParserSpec
    return _SPEC
