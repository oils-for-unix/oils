#!/usr/bin/env python2
"""
ysh_ify_test.py: Tests for ysh_ify.py
"""

import unittest

from _devbuild.gen.runtime_asdl import word_style_e
from osh import word_
from tools import ysh_ify  # module under test

from osh.word_parse_test import _assertReadWord


def assertStyle(test, expected_style, word_str):
    w = _assertReadWord(test, word_str)

    new_word = word_.TildeDetect(w)
    if new_word is not None:
        w = new_word

    actual = ysh_ify._GetRhsStyle(w)
    test.assertEqual(expected_style, actual)


class FixTest(unittest.TestCase):
    def testGetRhsStyle(self):
        w = assertStyle(self, word_style_e.SQ, 'foo')
        w = assertStyle(self, word_style_e.SQ, "'hi'")

        w = assertStyle(self, word_style_e.DQ, '$var')
        w = assertStyle(self, word_style_e.Unquoted, '${var}')

        w = assertStyle(self, word_style_e.DQ, ' "$var" ')
        w = assertStyle(self, word_style_e.DQ, ' "${var}" ')

        w = assertStyle(self, word_style_e.Unquoted, ' $((1+2)) ')
        w = assertStyle(self, word_style_e.Unquoted, ' $(echo hi) ')

        w = assertStyle(self, word_style_e.DQ, ' "$((1+2))" ')
        w = assertStyle(self, word_style_e.DQ, ' "$(echo hi)" ')

        w = assertStyle(self, word_style_e.DQ, ' $src/file ')
        w = assertStyle(self, word_style_e.DQ, ' ${src}/file ')

        w = assertStyle(self, word_style_e.DQ, ' "$src/file" ')
        w = assertStyle(self, word_style_e.DQ, ' "${src}/file" ')

        w = assertStyle(self, word_style_e.DQ, ' $((1+2))$(echo hi) ')

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

        w = assertStyle(self, word_style_e.DQ, ' ~/src ')
        w = assertStyle(self, word_style_e.DQ, ' ~bob/foo ')

        # Could be single quoted
        w = assertStyle(self, word_style_e.DQ, 'notleading~')

        # These tildes are quoted
        w = assertStyle(self, word_style_e.DQ, ' "~/src" ')
        w = assertStyle(self, word_style_e.DQ, ' "~bob/foo" ')


if __name__ == '__main__':
    unittest.main()
