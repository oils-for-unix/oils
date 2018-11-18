#!/usr/bin/python -S
from __future__ import print_function
"""
ui_test.py: Tests for ui.py
"""

import unittest

from core import state
from core import test_lib
from core.meta import runtime

from core import ui  # module under test

value = runtime.value


class UiTest(unittest.TestCase):

  def testPrompt(self):
    arena = test_lib.MakeArena('<ui_test.py>')
    mem = state.Mem('', [], {}, arena)

    ex = test_lib.InitExecutor(arena=arena)

    p = ui.Prompt('osh', arena, ex.parse_ctx, ex, mem)

    # Rgression for caching bug!
    self.assertEqual('foo', p.EvalPrompt(value.Str('foo')))
    self.assertEqual('foo', p.EvalPrompt(value.Str('foo')))


if __name__ == '__main__':
  unittest.main()
