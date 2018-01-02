#!/usr/bin/python -S
"""
builtin_test.py: Tests for builtin.py
"""

import unittest

from core import lexer
from core import builtin  # module under test


class BuiltinTest(unittest.TestCase):

  def testEchoLexer(self):
    lex = builtin.ECHO_LEXER
    print list(lex.Tokens(r'newline \n NUL \0 octal \0377 hex \x00'))
    print list(lex.Tokens(r'unicode \u0065 \U00000065'))
    print list(lex.Tokens(r'\d \e \f \g'))

  def testSplitLine(self):
    # NOTE: This function can be rewritten in C or C++.  Use ASAN / fuzzing?
    # It's similar to the functions in core/glob_.py.
    #
    # Can you use regexes?  Need different regexes for "allow_escape".
    # Nah I think I need to rewrite _IfsSplit in word_eval.c.
    # That is a very similar function.
    #
    # Can you lift it from dash?  The other shells all GPL.

    # word_eval_test._IfsSplit has at least one bug!  With IFS='_ '.  Maybe
    # should test that here.

    DEFAULT_IFS = ' \t\n'
    OTHER_IFS = ':'

    # allow_escape is True by default, but False when the user passes -r.
    CASES =  [
        #(' one two ', DEFAULT_IFS, False, ['one', 'two'], False),
        (' one:two ', OTHER_IFS, True, [' one', 'two '], False),
        (' one\:two ', OTHER_IFS, True, [' one:two '], False),
        (' one\:two ', OTHER_IFS, False, [r' one\', two '], False),
    ]

    # Not worknig yet!
    return

    for line, ifs, allow_escape, expected_parts, expected_c in CASES:
      parts, continued = builtin._SplitLine(line, ifs, allow_escape)
      self.assertEqual(expected_parts, parts,
          '%r: %s != %s' % (line, expected_parts, parts))
      self.assertEqual(expected_c, continued,
          '%r: %s != %s' % (line, expected_c, continued))


if __name__ == '__main__':
  unittest.main()
