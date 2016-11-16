#!/usr/bin/python3
"""
arith_parse.py - Parse shell arithmetic, which is based on C.

TODO:
- fix main()
"""

import sys

from core import tdop
from core.tokens import *
from core.arith_node import UnaryANode, BinaryANode, TernaryANode
#from tokenize import tokenize_expr
#from parse_util import CompositeNode


def NullIncDec(p, t, bp):
  """ ++x or ++x[1] """
  right = p.ParseUntil(bp)
  if right.atype not in tdop.LVALUE_TYPES:
    raise tdop.ParseError("Can't assign to %r (%s)" % (right, right.token))
  return UnaryANode(t.AType(), right)


def NullUnaryPlus(p, t, bp):
  """ +x, to distinguish from binary operator. """
  right = p.ParseUntil(bp)
  return UnaryANode(NODE_UNARY_PLUS, right)


def NullUnaryMinus(p, t, bp):
  """ -1, to distinguish from binary operator. """
  right = p.ParseUntil(bp)
  return UnaryANode(NODE_UNARY_MINUS, right)


def LeftIncDec(p, t, left, rbp):
  """ For i++ and i--
  """
  if left.atype not in tdop.LVALUE_TYPES:
    raise tdop.ParseError("Can't assign to %r (%s)" % (left, left.token))
  if t.AType() == AS_OP_DPLUS:
    atype = NODE_POST_DPLUS
  elif t.AType() == AS_OP_DMINUS:
    atype = NODE_POST_DMINUS
  else:
    raise AssertionError
  return UnaryANode(t.AType(), left)


def LeftIndex(p, t, left, unused_bp):
  """ index f[x+1] """
  # f[x] or f[x][y]
  if left.atype not in tdop.CALL_INDEX_TYPES:
    raise tdop.ParseError("%s can't be indexed" % left)
  index = p.ParseUntil(0)
  p.Eat(AS_OP_RBRACKET)

  return BinaryANode(t.AType(), left, index)


def LeftTernary(p, t, left, bp):
  """ Function call f(a, b). """
  true_expr = p.ParseUntil(bp)
  p.Eat(AS_OP_COLON)
  false_expr = p.ParseUntil(bp)
  children = [left, true_expr, false_expr]
  return TernaryANode(t.AType(), left, true_expr, false_expr)


# For overloading of , inside function calls
COMMA_PREC = 1

def LeftFuncCall(p, t, left, unused_bp):
  """ Function call f(a, b). """
  children = [left]
  # f(x) or f[i](x)
  if left.atype not in tdop.CALL_INDEX_TYPES:
    raise tdop.ParseError("%s can't be called" % left)
  while not p.AtToken(AS_OP_RPAREN):
    # We don't want to grab the comma, e.g. it is NOT a sequence operator.  So
    # set the precedence to 5.
    children.append(p.ParseUntil(COMMA_PREC))
    if p.AtToken(','):
      p.Next()
  p.Eat(AS_OP_RPAREN)
  t.type = 'call'
  return CompositeNode(t, children)


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

  # TODO: Could these work as kinds?
  spec.Null(-1, tdop.NullConstant, [
      NODE_ARITH_WORD,
      AS_OP_AT,  # For ${a[@]}
      AS_OP_STAR,  # For ${a[*]}
      AS_OP_SEMI,  # for loop
      ])
  spec.Null(-1, tdop.NullError, [
      AS_OP_RPAREN, AS_OP_RBRACKET, AS_OP_COLON,
      Eof_REAL, Eof_RPAREN, Eof_BACKTICK,
      # Not in the arithmetic language, but is a cmomon terminator , e.g. ${foo:1}
      AS_OP_RBRACE,
      ])

  # 0 precedence -- doesn't bind until )
  spec.Null(0, tdop.NullParen, [AS_OP_LPAREN])  # for grouping

  spec.Left(33, LeftIncDec, [AS_OP_DPLUS, AS_OP_DMINUS])
  spec.Left(33, LeftFuncCall, [AS_OP_LPAREN])
  spec.Left(33, LeftIndex, [AS_OP_LBRACKET])

  # 31 -- binds to everything except function call, indexing, postfix ops
  spec.Null(31, NullIncDec, [AS_OP_DPLUS, AS_OP_DMINUS])
  spec.Null(31, NullUnaryPlus, [AS_OP_PLUS])
  spec.Null(31, NullUnaryMinus, [AS_OP_MINUS])
  spec.Null(31, tdop.NullPrefixOp, [AS_OP_BANG, AS_OP_TILDE])

  # Right associative: 2 ** 3 ** 2 == 2 ** (3 ** 2)
  # NOTE: This isn't in C
  spec.LeftRightAssoc(29, tdop.LeftBinaryOp, [AS_OP_DSTAR])

  # * / %
  spec.Left(27, tdop.LeftBinaryOp, [AS_OP_STAR, AS_OP_SLASH, AS_OP_PERCENT])

  spec.Left(25, tdop.LeftBinaryOp, [AS_OP_PLUS, AS_OP_MINUS])
  spec.Left(23, tdop.LeftBinaryOp, [AS_OP_DLESS, AS_OP_DGREAT]) 
  spec.Left(21, tdop.LeftBinaryOp, [
    AS_OP_LESS, AS_OP_GREAT, AS_OP_LE, AS_OP_GE])

  spec.Left(19, tdop.LeftBinaryOp, [AS_OP_NEQUAL, AS_OP_DEQUAL])

  spec.Left(15, tdop.LeftBinaryOp, [AS_OP_AMP])
  spec.Left(13, tdop.LeftBinaryOp, [AS_OP_CARET])
  spec.Left(11, tdop.LeftBinaryOp, [AS_OP_PIPE])
  spec.Left(9, tdop.LeftBinaryOp, [AS_OP_DAMP])
  spec.Left(7, tdop.LeftBinaryOp, [AS_OP_DPIPE])

  spec.Left(5, LeftTernary, [AS_OP_QMARK])

  # Right associative: a = b = 2 is a = (b = 2)
  spec.LeftRightAssoc(3, tdop.LeftAssign, [
      AS_OP_EQUAL,
      AS_OP_PLUS_EQUAL, AS_OP_MINUS_EQUAL, AS_OP_STAR_EQUAL, AS_OP_SLASH_EQUAL,
      AS_OP_PERCENT_EQUAL,
      AS_OP_DLESS_EQUAL, AS_OP_DGREAT_EQUAL, AS_OP_AMP_EQUAL,
      AS_OP_CARET_EQUAL, AS_OP_PIPE_EQUAL])

  spec.Left(COMMA_PREC, tdop.LeftBinaryOp, [AS_OP_COMMA])

  return spec


def MakeParser(s):
  spec = MakeShellSpec()
  lexer = tokenize_expr(s)
  p = tdop.TdopParser(spec, lexer)
  return p


def ParseShell(s, expected=None):
  p = MakeParser(s)
  tree = p.Parse()

  tdop.Assert(s, expected, tree)
  return tree


def main(argv):
  s = argv[1]

  tree = ParseShell(s)
  print(tree)


if __name__ == '__main__':
  main(sys.argv)
