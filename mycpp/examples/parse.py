#!/usr/bin/python
"""
parse.py
"""
from __future__ import print_function

import os
from typing import Tuple
from runtime import log
from _gen.expr_asdl import (
    expr_t, expr__Var, expr__Const, expr__Binary, id_e, id_t
)


class Lexer(object):
  # "type declaration" of members

  def __init__(self, s):
    # type: (str) -> None
    self.s = s
    self.i = 0
    self.n = len(s)

  def Read(self):
    # type: () -> Tuple[id_t, str]
    if self.i >= self.n:
      return id_e.Eof, ''  # sentinel

    tok = self.s[self.i]
    self.i += 1

    if tok.isdigit():
      return id_e.Const, tok
    if tok.isalpha():
      return id_e.Var, tok
    if tok in '+-':
      return id_e.Op1, tok  # lower precedence
    if tok in '*/':
      return id_e.Op2, tok  # higher precedence
    if tok in '()':
      return id_e.Paren, tok

    raise AssertionError()

  def _MethodCallingOtherMethod(self):
    # type: () -> None
    # Make sure we don't get a member var called Read!
    # This is easy because we're only checking assignment statements.
    self.Read()


class Parser(object):
  """
  Grammar from http://compilers.iecc.com/crenshaw/tutor6.txt, adapted to ANTLR
  syntax.

    Expr    = Term ('+' Term)*
    Term    = Factor ('*' Factor)*
    Factor  = VAR
            | CONST
            | '(' Expr ')'
  """
  def __init__(self, lexer):
    # type: (Lexer) -> None
    self.lexer = lexer  
    self.tok_type = id_e.Eof  # type: id_t
    self.tok_val = ''

  def Next(self):
    # type: () -> None
    self.tok_type, self.tok_val = self.lexer.Read()
    #log('-- %r %r', self.tok_type, self.tok_val)

  def Eat(self, tok_val):
    # type: (str) -> None
    if self.tok_val != tok_val:
      raise RuntimeError('Expected %r, got %r' % (tok_val, self.tok_val))
    self.Next()

  def ParseFactor(self):
    # type: () -> expr_t

    #log('ParseFactor')
    if self.tok_type == id_e.Var:
      n1 = expr__Var(self.tok_val)
      self.Next()
      return n1

    if self.tok_type == id_e.Const:
      n2 = expr__Const(int(self.tok_val))
      self.Next()
      return n2

    if self.tok_type == id_e.Paren:
      self.Eat('(')
      n3 = self.ParseExpr()
      self.Eat(')')
      return n3

    raise AssertionError('%s %s' % (self.tok_type, self.tok_val))

  def ParseTerm(self):
    # type: () -> expr_t

    #log('ParseTerm')
    node = self.ParseFactor()

    # TODO: Iterate and create nodes
    while self.tok_type == id_e.Op2:
      op = self.tok_val
      self.Next()
      n2 = self.ParseFactor()
      node = expr__Binary(op, node, n2)
    return node

  def ParseExpr(self):
    # type: () -> expr_t

    #log('ParseExpr')
    node = self.ParseTerm()

    while self.tok_type == id_e.Op1:
      op = self.tok_val
      self.Next()
      n2 = self.ParseTerm()
      node = expr__Binary(op, node, n2)
    return node

  def Parse(self):
    # type: () -> expr_t
    self.Next()
    return self.ParseExpr()


def run_tests():
  # type: () -> None
  lex = Lexer('abc')
  while True:
    tok_type, tok_val = lex.Read()
    if tok_type == id_e.Eof:
      break
    print('%s %s' % (tok_type, tok_val))

  for expr in ['1+2', '1+2*3', '1*2+3', '(1+2)*3', 'a+b+c+d', 'a*b*3*4']:
    lex = Lexer(expr)
    p = Parser(lex)
    log('')
    log('--')
    log('%s =>', expr)
    log('%s', p.Parse())


def run_benchmarks():
  # type: () -> None
  n = 200000

  result = 0
  i = 0
  while i < n:
    lex = Lexer('abc')
    while True:
      tok = lex.Read()
      if tok is None:
        break
      result += len(tok)

    i += 1

  log('result = %d', result)
  log('iterations = %d', n)


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
