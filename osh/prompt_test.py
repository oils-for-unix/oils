#!/usr/bin/env python2
"""
prompt_test.py: Tests for prompt.py
"""
from __future__ import print_function

import unittest

from _devbuild.gen.runtime_asdl import value
from core import test_lib
from frontend import match
from core import state
from osh import prompt  # module under test


class PromptTest(unittest.TestCase):

  def setUp(self):
    arena = test_lib.MakeArena('<ui_test.py>')
    mem = state.Mem('', [], arena, [])
    parse_ctx = test_lib.InitParseContext()
    self.p = prompt.Evaluator('osh', parse_ctx, mem)
    # note: this has a separate 'mem' object
    self.p.word_ev = test_lib.InitWordEvaluator()

  def testEvaluator(self):
    # Regression for caching bug!
    self.assertEqual('foo', self.p.EvalPrompt(value.Str('foo')))
    self.assertEqual('foo', self.p.EvalPrompt(value.Str('foo')))

  def testNoEscapes(self):
    for prompt_str in ["> ", "osh>", "[[]][[]][][]]][["]:
      self.assertEqual(self.p.EvalPrompt(value.Str(prompt_str)), prompt_str)

  def testValidEscapes(self):
    for prompt_str in [
        "\[\033[01;34m\]user\[\033[00m\] >", r"\[\]\[\]\[\]",
        r"\[\] hi \[hi\] \[\] hello"]:
      self.assertEqual(
          self.p.EvalPrompt(value.Str(prompt_str)),
          prompt_str.replace(r"\[", "\x01").replace(r"\]", "\x02"))

  def testInvalidEscapes(self):
    for invalid_prompt in [
        r"\[\[", r"\[\]\[\]\]", r"\]\]", r"almost valid \]", r"\[almost valid",
        r"\]\[",  # goes negative!
        ]:
      tokens = match.Ps1Tokens(invalid_prompt)
      self.assertEqual(
          prompt.PROMPT_ERROR, self.p._ReplaceBackslashCodes(tokens))


if __name__ == '__main__':
  unittest.main()
