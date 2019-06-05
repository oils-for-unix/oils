#!/usr/bin/env python2
"""
arith_parse.py: Parse shell-like and C-like arithmetic.
"""
from __future__ import print_function

import sys

import tdop
from tdop import CompositeNode

import demo_asdl

arith_expr = demo_asdl.arith_expr
op_id_e = demo_asdl.op_id_e


#
# Null Denotation -- token that takes nothing on the left
#

def NullConstant(p, token, bp):
  if token.type == 'number':
    return arith_expr.Const(token.val)
  # We have to wrap a string in some kind of variant.
  if token.type == 'name':
    return arith_expr.ArithVar(token.val)

  raise AssertionError(token.type)


def NullParen(p, token, bp):
  """ Arithmetic grouping """
  r = p.ParseUntil(bp)
  p.Eat(')')
  return r


def NullPrefixOp(p, token, bp):
  """Prefix operator.

  Low precedence:  return, raise, etc.
    return x+y is return (x+y), not (return x) + y

  High precedence: logical negation, bitwise complement, etc.
    !x && y is (!x) && y, not !(x && y)
  """
  r = p.ParseUntil(bp)
  return CompositeNode(token, [r])


def NullIncDec(p, token, bp):
  """ ++x or ++x[1] """
  right = p.ParseUntil(bp)
  if right.token.type not in ('name', 'get'):
    raise tdop.ParseError("Can't assign to %r (%s)" % (right, right.token))
  return CompositeNode(token, [right])


#
# Left Denotation -- token that takes an expression on the left
#

def LeftIncDec(p, token, left, rbp):
  """ For i++ and i--
  """
  if left.token.type not in ('name', 'get'):
    raise tdop.ParseError("Can't assign to %r (%s)" % (left, left.token))
  token.type = 'post' + token.type
  return CompositeNode(token, [left])


def LeftIndex(p, token, left, unused_bp):
  """ index f[x+1] """
  # f[x] or f[x][y]
  if not isinstance(left, demo_asdl.ArithVar):
    raise tdop.ParseError("%s can't be indexed" % left)
  index = p.ParseUntil(0)
  if p.AtToken(':'):
    p.Next()
    end = p.ParseUntil(0)
  else:
    end = None

  p.Eat(']')

  # TODO: If you see ], then
  # 1:4
  # 1:4:2
  # Both end and step are optional

  if end:
    return demo_asdl.Slice(left, index, end, None)
  else:
    return demo_asdl.Index(left, index)


def LeftTernary(p, token, left, bp):
  """ e.g. a > 1 ? x : y """
  true_expr = p.ParseUntil(bp)
  p.Eat(':')
  false_expr = p.ParseUntil(bp)
  children = [left, true_expr, false_expr]
  return CompositeNode(token, children)


def LeftBinaryOp(p, token, left, rbp):
  """ Normal binary operator like 1+2 or 2*3, etc. """
  if token.val == '+':
    op_id_ = op_id_e.Plus
  elif token.val == '-':
    op_id_ = op_id_e.Minus
  elif token.val == '*':
    op_id_ = op_id_e.Star
  else:
    raise AssertionError(token.val)
  return arith_expr.ArithBinary(op_id_, left, p.ParseUntil(rbp))


def LeftAssign(p, token, left, rbp):
  """ Normal binary operator like 1+2 or 2*3, etc. """
  # x += 1, or a[i] += 1
  if left.token.type not in ('name', 'get'):
    raise tdop.ParseError("Can't assign to %r (%s)" % (left, left.token))
  return CompositeNode(token, [left, p.ParseUntil(rbp)])


def LeftComma(p, token, left, rbp):
  """ foo, bar, baz

  Could be sequencing operator, or tuple without parens
  """
  r = p.ParseUntil(rbp)
  if left.token.type == ',':  # Keep adding more children
    left.children.append(r)
    return left
  children = [left, r]
  return CompositeNode(token, children)


# For overloading of , inside function calls
COMMA_PREC = 1

def LeftFuncCall(p, token, left, unused_bp):
  """ Function call f(a, b). """
  args = []
  # f(x) or f[i](x)
  if not isinstance(left, demo_asdl.ArithVar):
    raise tdop.ParseError("%s can't be called" % left)
  func_name = left.name  # get a string

  while not p.AtToken(')'):
    # We don't want to grab the comma, e.g. it is NOT a sequence operator.  So
    # set the precedence to 5.
    args.append(p.ParseUntil(COMMA_PREC))
    if p.AtToken(','):
      p.Next()
  p.Eat(")")
  return demo_asdl.FuncCall(func_name, args)


def MakeShellParserSpec():
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

  spec.Left(COMMA_PREC, LeftComma, [','])

  # 0 precedence -- doesn't bind until )
  spec.Null(0, NullParen, ['('])  # for grouping

  # -1 precedence -- never used
  spec.Null(-1, NullConstant, ['name', 'number'])
  spec.Null(-1, tdop.NullError, [')', ']', ':', 'eof'])

  return spec


def MakeParser(s):
  """Used by tests."""
  spec = MakeShellParserSpec()
  lexer = tdop.Tokenize(s)
  p = tdop.Parser(spec, lexer)
  return p


def ParseShell(s, expected=None):
  """Used by tests."""
  p = MakeParser(s)
  tree = p.Parse()

  sexpr = repr(tree)
  if expected is not None:
    assert sexpr == expected, '%r != %r' % (sexpr, expected)

  #print('%-40s %s' % (s, sexpr))
  return tree


def main(argv):
  try:
    s = argv[1]
  except IndexError:
    print('Usage: ./arith_parse.py EXPRESSION')
  else:
    try:
      tree = ParseShell(s)
    except tdop.ParseError as e:
      print('Error parsing %r: %s' % (s, e), file=sys.stderr)
    print(tree)


if __name__ == '__main__':
  main(sys.argv)
