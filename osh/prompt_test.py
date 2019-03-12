#!/usr/bin/python -S
"""
prompt_test.py: Tests for prompt.py
"""
from __future__ import print_function

import unittest

from _devbuild.gen.runtime_asdl import value
from core import test_lib
from osh import state
from osh import prompt  # module under test


class PromptTest(unittest.TestCase):

  def testEvaluator(self):
    arena = test_lib.MakeArena('<ui_test.py>')
    mem = state.Mem('', [], {}, arena)

    ex = test_lib.InitExecutor(arena=arena)

    p = prompt.Evaluator('osh', arena, ex.parse_ctx, ex, mem)

    # Rgression for caching bug!
    self.assertEqual('foo', p.EvalPrompt(value.Str('foo')))
    self.assertEqual('foo', p.EvalPrompt(value.Str('foo')))


if __name__ == '__main__':
  unittest.main()
