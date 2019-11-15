#!/usr/bin/python
"""
parse.py
"""
from __future__ import print_function

import os
import sys

# PYTHONPATH=$REPO_ROOT/vendor
from typing import Tuple, Optional, cast

# PYTHONPATH=$REPO_ROOT/mycpp
from mycpp.mylib import log, tagswitch
from mycpp import mylib
from _gen.expr_asdl import (
    expr_e,  # for translation only?
    expr_t, expr__Var, expr__Const, expr__Binary, tok_e, tok_t
)

# PYTHONPATH=$REPO_ROOT
from asdl import format as fmt


class Lexer(object):
  # "type declaration" of members

  def __init__(self, s):
    # type: (str) -> None
    self.s = s
    self.i = 0
    self.n = len(s)

  def Read(self):
    # type: () -> Tuple[tok_t, str]
    if self.i >= self.n:
      return tok_e.Eof, ''  # sentinel

    tok = self.s[self.i]
    self.i += 1

    if tok.isdigit():
      return tok_e.Const, tok
    if tok.isalpha():
      return tok_e.Var, tok
    if tok in '+-':
      return tok_e.Op1, tok  # lower precedence
    if tok in '*/':
      return tok_e.Op2, tok  # higher precedence
    if tok in '()':
      return tok_e.Paren, tok

    return tok_e.Invalid, tok

  def _MethodCallingOtherMethod(self):
    # type: () -> None
    # Make sure we don't get a member var called Read!
    # This is easy because we're only checking assignment statements.
    self.Read()


class ParseError(Exception):
  def __init__(self, msg):
    # type: (str) -> None
    self.msg = msg


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
    self.tok_type = tok_e.Eof  # type: tok_t
    self.tok_val = ''

  def Next(self):
    # type: () -> None
    self.tok_type, self.tok_val = self.lexer.Read()
    #log('-- %r %r', self.tok_type, self.tok_val)

  def Eat(self, tok_val):
    # type: (str) -> None
    if self.tok_val != tok_val:
      #raise ParseError('Expected %r, got %r' % (tok_val, self.tok_val))
      raise ParseError('Expected ' + tok_val)
    self.Next()

  def ParseFactor(self):
    # type: () -> expr_t

    #log('ParseFactor')
    if self.tok_type == tok_e.Var:
      n1 = expr__Var(self.tok_val)
      self.Next()
      return n1

    if self.tok_type == tok_e.Const:
      n2 = expr__Const(int(self.tok_val))
      self.Next()
      return n2

    if self.tok_type == tok_e.Paren:
      self.Eat('(')
      n3 = self.ParseExpr()
      self.Eat(')')
      return n3

    #raise ParseError('Unexpected token %s %s' % (self.tok_type, self.tok_val))
    raise ParseError('Unexpected token ' + self.tok_val)

  def ParseTerm(self):
    # type: () -> expr_t

    #log('ParseTerm')
    node = self.ParseFactor()

    # TODO: Iterate and create nodes
    while self.tok_type == tok_e.Op2:
      op = self.tok_val
      self.Next()
      n2 = self.ParseFactor()
      node = expr__Binary(op, node, n2)
    return node

  def ParseExpr(self):
    # type: () -> expr_t

    #log('ParseExpr')
    node = self.ParseTerm()

    while self.tok_type == tok_e.Op1:
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
    if tok_type == tok_e.Eof:
      break
    #print('%s %s' % (tok_type, tok_val))
    log('tok_val %s', tok_val)

  CASES = [
      '1+2', '1+2*3', '1*2+3', '(1+2)*3', 'a+b+c+d', 'a*b*3*4',
      '1', 'a',

      # expect errors here:
      '(',
      ')',
      '(a+b',
      ' ',
      ' $$ ',
  ]
  for expr in CASES:
    lex = Lexer(expr)
    p = Parser(lex)
    log('')
    log('--')
    log('%s =>', expr)

    node = None  # type: Optional[expr_t]
    try:
      node = p.Parse()
    except ParseError as e:
      log('Parse error: %s', e.msg)
      continue

    #log('%s', tree)

    htree = node.AbbreviatedTree()
    ast_f = fmt.AnsiOutput(mylib.Stdout())

    fmt.PrintTree(htree, ast_f)
    ast_f.write('\n')

    UP_node = node
    with tagswitch(UP_node) as case:
      if case(expr_e.Const):
        node = cast(expr__Const, UP_node)
        log('Const %d', node.i)

      elif case(expr_e.Var):
        node = cast(expr__Var, UP_node)
        log('Var %s', node.name)

      else:
        log('Other')


def run_benchmarks():
  # type: () -> None
  n = 200000

  result = 0
  i = 0
  while i < n:
    lex = Lexer('a*b*3*4')
    p = Parser(lex)
    tree = p.Parse()

    i += 1

  log('result = %d', result)
  log('iterations = %d', n)


if __name__ == '__main__':
  if os.getenv('BENCHMARK'):
    log('Benchmarking...')
    run_benchmarks()
  else:
    run_tests()
