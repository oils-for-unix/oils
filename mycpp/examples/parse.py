#!/usr/bin/python
"""
parse.py
"""
from __future__ import print_function

import os

from runtime import log


class Lexer(object):
  # "type declaration" of members

  def __init__(self, s):
    # type: (str) -> None
    self.s = s
    self.i = 0
    self.n = len(s)

  def Read(self):
    # type: () -> str
    if self.i >= self.n:
      return None  # sentinel

    tok = self.s[self.i]
    self.i += 1
    return tok

  def _MethodCallingOtherMethod(self):
    # type: () -> None
    # Make sure we don't get a member var called Read!
    # This is easy because we're only checking assignment statements.
    self.Read()


class Parser(object):
  def __init__(self, lexer):
    # type: (Lexer) -> None
    self.lexer = lexer  

  def Parse(self):
    # type: () -> str
    return "[parsed]"


def run_tests():
  # type: () -> None
  lex = Lexer('abc')
  while True:
    tok = lex.Read()
    if tok is None:
      break
    print(tok)

  p = Parser(lex)
  log("%s", p.Parse())


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
