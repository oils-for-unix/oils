#!/usr/bin/env python2

import unittest

from hypothesis import given
from hypothesis.strategies import text

from comp_ui import _PromptLen

class PromptTest(unittest.TestCase):
    @given(text())
    def testNeverPanics(self, s):
        self.assertIs(_PromptLen(s) >= 0, True)

if __name__ == '__main__':
    unittest.main()
