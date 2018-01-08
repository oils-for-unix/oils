#!/usr/bin/python -S
"""
lex_gen_test.py: Tests for lex_gen.py
"""

import unittest

from osh import lex
from core import lexer_gen  # module under test


class LexerGenTest(unittest.TestCase):

  def testTranslateRegex(self):
    PAIRS = [
        (r'a', r'"a" '),
        (r'[a-z]', r'[a-z]'),
        (r'[a-zA-Z.]+', r'[a-zA-Z.]+ '),
        (r'[a-zA-Z_][a-zA-Z0-9_]*\+?=', r'[a-zA-Z_][a-zA-Z0-9_]* "+" ? "=" '),

        (r'[."]*', r'[."]* '),
        (r'\$', r'"$" '),
        (r'.*', r'.* '),

        # Both of these accepted?
        ('\0', r'"\x00" '),
        (r'\0', r'"\x00" '),
        (r'\\', r'"\\" '),
        (r'[\\]', r'"\\" '),

        (r'.', r'.'),
        (r'[^a]', r'[^a]'),
        (r'[^a-z]', r'[^a-z]'),
        # . isn't special inside
        (r'[a\.]', r'[a.]'),

        (r'[0-7]{1,3}', r'[0-7]{1,3} '),
    ]
    for py, expected in PAIRS:
      #self.assertEqual(expected, lexer_gen.TranslateRegex(py))
      print '---', py
      actual = lexer_gen.TranslateRegex(py)
      print repr(actual)
      self.assertEqual(expected, actual)
      print
      print


if __name__ == '__main__':
  unittest.main()
