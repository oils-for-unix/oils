#!/usr/bin/python -S
"""
builtin_test.py: Tests for builtin.py
"""

import unittest

from core import legacy
from core import lexer
from core import builtin  # module under test


class BuiltinTest(unittest.TestCase):

  def testEchoLexer(self):
    lex = builtin.ECHO_LEXER
    print list(lex.Tokens(r'newline \n NUL \0 octal \0377 hex \x00'))
    print list(lex.Tokens(r'unicode \u0065 \U00000065'))
    print list(lex.Tokens(r'\d \e \f \g'))

  def testAppendParts(self):
    # allow_escape is True by default, but False when the user passes -r.
    CASES =  [
        (['Aa', 'b', ' a b'], 'Aa b \\ a\\ b'),
    ]

    for expected_parts, line in CASES:
      sp = legacy.IfsSplitter(legacy.DEFAULT_IFS, '')
      spans = sp.Split(line, True)
      parts = []
      builtin._AppendParts(line, spans, 100, False, parts)
      self.assertEqual(expected_parts, parts)


if __name__ == '__main__':
  unittest.main()
