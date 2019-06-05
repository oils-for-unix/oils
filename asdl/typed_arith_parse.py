#!/usr/bin/env python2
"""
typed_arith_parse.py: Parse shell-like and C-like arithmetic.
"""
from __future__ import print_function

import sys

from _devbuild.gen.typed_arith_asdl import (
    arith_expr_t, arith_expr__Binary, arith_expr__FuncCall, arith_expr__Const,
    arith_expr__Var, arith_expr__Unary, arith_expr__Binary, arith_expr__Ternary,
    arith_expr__Index, arith_expr__Slice
)

from typing import Dict, List, Optional
#from typing import cast

from asdl import tdop
from asdl import tdop_lexer


#
# Null Denotation -- token that takes nothing on the left
#

def NullConstant(p, token, bp):
  # type: (tdop.Parser, tdop.Token, int) -> arith_expr_t
  if token.type == 'number':
    return arith_expr__Const(int(token.val))
  # We have to wrap a string in some kind of variant.
  if token.type == 'name':
    return arith_expr__Var(token.val)

  raise AssertionError(token.type)


def NullParen(p, token, bp):
  # type: (tdop.Parser, tdop.Token, int) -> arith_expr_t
  """ Arithmetic grouping """
  r = p.ParseUntil(bp)
  p.Eat(')')
  return r


def NullPrefixOp(p, token, bp):
  # type: (tdop.Parser, tdop.Token, int) -> arith_expr_t
  """Prefix operator.

  Low precedence:  return, raise, etc.
    return x+y is return (x+y), not (return x) + y

  High precedence: logical negation, bitwise complement, etc.
    !x && y is (!x) && y, not !(x && y)
  """
  r = p.ParseUntil(bp)
  return arith_expr__Unary(token.val, r)


def NullIncDec(p, token, bp):
  # type: (tdop.Parser, tdop.Token, int) -> arith_expr_t
  """ ++x or ++x[1] """
  right = p.ParseUntil(bp)
  if not isinstance(right, (arith_expr__Var, arith_expr__Index)):
    raise tdop.ParseError("Can't assign to %r" % right)
  return arith_expr__Unary(token.val, right)


#
# Left Denotation -- token that takes an expression on the left
#

def LeftIncDec(p, token, left, rbp):
  # type: (tdop.Parser, tdop.Token, arith_expr_t, int) -> arith_expr_t
  """ For i++ and i-- """
  if not isinstance(left, (arith_expr__Var, arith_expr__Index)):
    raise tdop.ParseError("Can't assign to %r" % left)
  token.type = 'post' + token.type
  return arith_expr__Unary(token.val, left)


def LeftIndex(p, token, left, unused_bp):
  # type: (tdop.Parser, tdop.Token, arith_expr_t, int) -> arith_expr_t
  """ index f[x+1] """
  # f[x] or f[x][y]
  if not isinstance(left, arith_expr__Var):
    raise tdop.ParseError("%s can't be indexed" % left)
  index = p.ParseUntil(0)
  if p.AtToken(':'):
    p.Next()
    end = p.ParseUntil(0)  # type: Optional[arith_expr_t]
  else:
    end = None

  p.Eat(']')

  # TODO: If you see ], then
  # 1:4
  # 1:4:2
  # Both end and step are optional

  if end:
    return arith_expr__Slice(left, index, end, None)
  else:
    return arith_expr__Index(left, index)


def LeftTernary(p, token, left, bp):
  # type: (tdop.Parser, tdop.Token, arith_expr_t, int) -> arith_expr_t
  """ e.g. a > 1 ? x : y """
  true_expr = p.ParseUntil(bp)
  p.Eat(':')
  false_expr = p.ParseUntil(bp)
  return arith_expr__Ternary(left, true_expr, false_expr)


def LeftBinaryOp(p, token, left, rbp):
  # type: (tdop.Parser, tdop.Token, arith_expr_t, int) -> arith_expr_t
  """ Normal binary operator like 1+2 or 2*3, etc. """
  return arith_expr__Binary(token.val, left, p.ParseUntil(rbp))


def LeftAssign(p, token, left, rbp):
  # type: (tdop.Parser, tdop.Token, arith_expr_t, int) -> arith_expr_t
  """ Normal binary operator like 1+2 or 2*3, etc. """
  # x += 1, or a[i] += 1
  if not isinstance(left, (arith_expr__Var, arith_expr__Index)):
    raise tdop.ParseError("Can't assign to %r" % left)
  node = arith_expr__Binary(token.val, left, p.ParseUntil(rbp))
  # For TESTING
  node.spids.append(42)
  node.spids.append(43)
  return node


# For overloading of , inside function calls
COMMA_PREC = 1

def LeftFuncCall(p, token, left, unused_bp):
  # type: (tdop.Parser, tdop.Token, arith_expr_t, int) -> arith_expr__FuncCall
  """ Function call f(a, b). """
  args = []  # type: List[arith_expr_t]
  # f(x) or f[i](x)
  if not isinstance(left, arith_expr__Var):
    raise tdop.ParseError("%s can't be called" % left)
  func_name = left.name  # get a string

  while not p.AtToken(')'):
    # We don't want to grab the comma, e.g. it is NOT a sequence operator.  So
    # set the precedence to 5.
    args.append(p.ParseUntil(COMMA_PREC))
    if p.AtToken(','):
      p.Next()
  p.Eat(")")
  return arith_expr__FuncCall(func_name, args)


def MakeShellParserSpec():
  # type: () -> tdop.ParserSpec
  """
  Create a parser.

  Compare the code below with this table of C operator precedence:
  http://en.cppreference.com/w/c/language/operator_precedence
  """
  spec = tdop.ParserSpec()

  spec.Left(31, LeftIncDec, ['++', '--'])
  spec.Left(31, LeftFuncCall, ['('])
  spec.Left(31, LeftIndex, ['['])

  # 29 -- binds to everything except function call, indexing, postfix ops
  spec.Null(29, NullIncDec, ['++', '--'])
  spec.Null(29, NullPrefixOp, ['+', '!', '~', '-'])

  # Right associative: 2 ** 3 ** 2 == 2 ** (3 ** 2)
  spec.LeftRightAssoc(27, LeftBinaryOp, ['**'])
  spec.Left(25, LeftBinaryOp, ['*', '/', '%'])

  spec.Left(23, LeftBinaryOp, ['+', '-'])
  spec.Left(21, LeftBinaryOp, ['<<', '>>'])
  spec.Left(19, LeftBinaryOp, ['<', '>', '<=', '>='])
  spec.Left(17, LeftBinaryOp, ['!=', '=='])

  spec.Left(15, LeftBinaryOp, ['&'])
  spec.Left(13, LeftBinaryOp, ['^'])
  spec.Left(11, LeftBinaryOp, ['|'])
  spec.Left(9, LeftBinaryOp, ['&&'])
  spec.Left(7, LeftBinaryOp, ['||'])

  spec.LeftRightAssoc(5, LeftTernary, ['?'])

  # Right associative: a = b = 2 is a = (b = 2)
  spec.LeftRightAssoc(3, LeftAssign, [
      '=',
      '+=', '-=', '*=', '/=', '%=',
      '<<=', '>>=', '&=', '^=', '|='])

  spec.Left(COMMA_PREC, LeftBinaryOp, [','])

  # 0 precedence -- doesn't bind until )
  spec.Null(0, NullParen, ['('])  # for grouping

  # -1 precedence -- never used
  spec.Null(-1, NullConstant, ['name', 'number'])
  spec.Null(-1, tdop.NullError, [')', ']', ':', 'eof'])

  return spec


def MakeParser(s):
  # type: (str) -> tdop.Parser
  """Used by tests."""
  spec = MakeShellParserSpec()
  lexer = tdop_lexer.Tokenize(s)
  p = tdop.Parser(spec, lexer)
  return p


def ParseShell(s, expected=None):
  # type: (str, Optional[str]) -> arith_expr_t
  """Used by tests."""
  p = MakeParser(s)
  tree = p.Parse()

  sexpr = repr(tree)
  if expected is not None:
    assert sexpr == expected, '%r != %r' % (sexpr, expected)

  #print('%-40s %s' % (s, sexpr))
  return tree


class Evaluator(object):
  def __init__(self):
    # type: () -> None
    self.mem = {}  # type: Dict[str, int]

  def Eval(self, node):
    # type: (arith_expr_t) -> int
    """Use the isinstance() style for comparison."""

    if isinstance(node, arith_expr__Const):
      assert node.i is not None
      return node.i

    if isinstance(node, arith_expr__Binary):
      assert node.left is not None
      assert node.right is not None

      left = self.Eval(node.left)
      right = self.Eval(node.right)
      op = node.op

      if op == '+':
        return left + right

    return 3

# NOTE: This doesn't translate yet because of cast().
"""
  def Eval2(self, node):
    # type: (arith_expr_t) -> int

    tag = node.tag
    if tag == arith_expr_e.Const:
      n = cast(arith_expr__Const, node)

      assert n.i is not None
      return n.i

    if tag == arith_expr_e.Binary:
      n2 = cast(arith_expr__Binary, node)

      assert n2.left is not None
      assert n2.right is not None

      left = self.Eval(n2.left)
      right = self.Eval(n2.right)
      op = n2.op

      if op == '+':
        return left + right

    return 3
"""


def main(argv):
  # type: (List[str]) -> int
  try:
    action = argv[1]
    s = argv[2]
  except IndexError:
    print('Usage: ./arith_parse.py ACTION EXPRESSION')
    return 2

  try:
    node = ParseShell(s)
  except tdop.ParseError as e:
    print('Error parsing %r: %s' % (s, e), file=sys.stderr)

  if action == 'parse':
    print(node)
  elif action == 'eval':
    ev = Evaluator()
    result = ev.Eval(node)
    print(node)
    print('  =>  ')
    print(result)
  else:
    print('Invalid action %r' % action)
    return 2

  return 0


if __name__ == '__main__':
  sys.exit(main(sys.argv))
