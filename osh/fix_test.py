#!/usr/bin/env python3
"""
fix_test.py: Tests for fix.py
"""

import unittest

from core import word
from osh import fix  # module under test
WordStyle = fix.WordStyle

from word_parse_test import _assertReadWord


def assertStyle(test, expected_style, word_str):
  w = _assertReadWord(test, word_str)

  new_word = word.TildeDetect(w)
  if new_word is not None:
    w = new_word

  actual = fix._GetRhsStyle(w)
  test.assertEqual(expected_style, actual)


class FixTest(unittest.TestCase):

  def testGetRhsStyle(self):
    w = assertStyle(self, WordStyle.SQ, 'foo')
    w = assertStyle(self, WordStyle.SQ, "'hi'")

    w = assertStyle(self, WordStyle.Expr, '$var')
    w = assertStyle(self, WordStyle.Expr, '${var}')

    w = assertStyle(self, WordStyle.Expr, ' "$var" ')
    w = assertStyle(self, WordStyle.Expr, ' "${var}" ')

    w = assertStyle(self, WordStyle.Unquoted, ' $((1+2)) ')
    w = assertStyle(self, WordStyle.Unquoted, ' $(echo hi) ')

    w = assertStyle(self, WordStyle.Unquoted, ' "$((1+2))" ')
    w = assertStyle(self, WordStyle.Unquoted, ' "$(echo hi)" ')

    w = assertStyle(self, WordStyle.DQ, ' $src/file ')
    w = assertStyle(self, WordStyle.DQ, ' ${src}/file ')

    w = assertStyle(self, WordStyle.DQ, ' "$src/file" ')
    w = assertStyle(self, WordStyle.DQ, ' "${src}/file" ')

    w = assertStyle(self, WordStyle.DQ, ' $((1+2))$(echo hi) ')

    # PROBLEM: How do you express it quoted?
    # "$~/src"
    # "$~bob/src"
    # Hm I guess this is OK ?

    # I think you need concatenation operator!    In expression mode

    # x = tilde() + "/src"
    # x = tilde('andy') + "/src"  # ~/src/

    # x = "$HOME/src"  # but this isn't the same -- $HOME might not be set!

    # x = "$tilde()/src"
    # x = "$tilde('andy')/src"  # Does this make sense?  A little ugly.



    w = assertStyle(self, WordStyle.DQ, ' ~/src ')
    w = assertStyle(self, WordStyle.DQ, ' ~bob/foo ')
    w = assertStyle(self, WordStyle.SQ, 'notleading~')

    # These tildes are quoted
    w = assertStyle(self, WordStyle.SQ, ' "~/src" ')
    w = assertStyle(self, WordStyle.SQ, ' "~bob/foo" ')


if __name__ == '__main__':
  unittest.main()
