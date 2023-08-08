#!/usr/bin/env python
"""
lexer_test.py: Tests for lexer.py
"""

import unittest

from osh.meta import Id
from osh.lex import LEXER_DEF

from osh.meta import ast


class TokenTest(unittest.TestCase):

  def testToken(self):
    t = ast.token(Id.Lit_Chars, 'abc')
    print(t)

    # This redundancy is OK I guess.
    t = ast.token(Id.Lit_LBrace, '{')
    print(t)

    t = ast.token(Id.Op_Semi, ';')
    print(t)

  def testPrintStats(self):
    states = sorted(
        LEXER_DEF.items(), key=lambda pair: len(pair[1]), reverse=True)
    total = 0
    for state, re_list in states:
      n = len(re_list)
      print(n, state)
      total += n

    print("Number of lex states: %d" % len(LEXER_DEF))
    print("Number of token dispatches: %d" % total)

  def testLineId(self):
    # TODO: Test that the lexer gives line_ids when passed an arena.
    # This might be more relevant if we start deallocating memory.
    pass


if __name__ == '__main__':
  unittest.main()
