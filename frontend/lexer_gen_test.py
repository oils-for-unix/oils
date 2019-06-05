#!/usr/bin/env python2
"""
lexer_gen_test.py: Tests for lexer_gen.py
"""
from __future__ import print_function

import unittest

from frontend import lexer_gen  # module under test
from core import test_lib


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
      print('--- %s' % test_lib.PrintableString(py))
      actual = lexer_gen.TranslateRegex(py)
      print(repr(actual))
      self.assertEqual(expected, actual)
      print()
      print()


if __name__ == '__main__':
  unittest.main()
