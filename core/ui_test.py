#!/usr/bin/python -S
from __future__ import print_function
"""
ui_test.py: Tests for ui.py
"""

import unittest

from core import test_lib
from osh.meta import runtime

from core import ui  # module under test


class UiTest(unittest.TestCase):

  def testPrompt(self):
    arena = test_lib.MakeArena('<ui_test.py>')
    ex = test_lib.InitExecutor(arena=arena)

    p = ui.Prompt(arena, ex.parse_ctx, ex)

    # Rgression for caching bug!
    self.assertEqual('foo', p.EvalPrompt(runtime.Str('foo')))
    self.assertEqual('foo', p.EvalPrompt(runtime.Str('foo')))


if __name__ == '__main__':
  unittest.main()
