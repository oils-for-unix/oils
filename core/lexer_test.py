#!/usr/bin/python3
"""
lexer_test.py: Tests for lexer.py
"""

import unittest

from core.id_kind import Id
from core.tokens import Token
from osh.lex import LEXER_DEF


class TokenTest(unittest.TestCase):

  def testToken(self):
    t = Token(Id.Lit_Chars, 'abc')
    print(t)

    # This redundancy is OK I guess.
    t = Token(Id.Lit_LBrace, '{')
    print(t)

    t = Token(Id.Op_Semi, ';')
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


if __name__ == '__main__':
  unittest.main()
