#!/usr/bin/env -S python -S
from __future__ import print_function
"""
builtin_test.py: Tests for builtin.py
"""

import unittest

from core import legacy
from core import builtin  # module under test


class BuiltinTest(unittest.TestCase):

  def testEchoLexer(self):
    lex = builtin.ECHO_LEXER
    print(list(lex.Tokens(r'newline \n NUL \0 octal \0377 hex \x00')))
    print(list(lex.Tokens(r'unicode \u0065 \U00000065')))
    print(list(lex.Tokens(r'\d \e \f \g')))

  def testAppendParts(self):
    # allow_escape is True by default, but False when the user passes -r.
    CASES = [
        (['Aa', 'b', ' a b'], 100, 'Aa b \\ a\\ b'),
        (['a', 'b', 'c'], 3, 'a b c '),
    ]

    for expected_parts, max_results, line in CASES:
      sp = legacy.IfsSplitter(legacy.DEFAULT_IFS, '')
      spans = sp.Split(line, True)
      print('--- %r' % line)
      for span in spans:
        print('  %s %s' % span)

      parts = []
      builtin._AppendParts(line, spans, max_results, False, parts)
      self.assertEqual(expected_parts, parts)

      print('---')


if __name__ == '__main__':
  unittest.main()
