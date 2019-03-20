#!/usr/bin/python -S
"""
prompt_test.py: Tests for prompt.py
"""
from __future__ import print_function

import unittest

from _devbuild.gen.runtime_asdl import value
from core import test_lib
from frontend import match
from osh import state
from osh import prompt  # module under test


class PromptTest(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    arena = test_lib.MakeArena('<ui_test.py>')
    mem = state.Mem('', [], {}, arena)
    ex = test_lib.InitExecutor(arena=arena)
    cls.p = prompt.Evaluator('osh', arena, ex.parse_ctx, ex, mem)

  def testEvaluator(self):
    # Regression for caching bug!
    self.assertEqual('foo', self.p.EvalPrompt(value.Str('foo')))
    self.assertEqual('foo', self.p.EvalPrompt(value.Str('foo')))

  def testNoEscapes(self):
    for prompt_str in ["> ", "osh>", "[[]][[]][][]]][["]:
      self.assertEqual(self.p.EvalPrompt(value.Str(prompt_str)), prompt_str)

  def testValidEscapes(self):
    for prompt_str in ["\[\033[01;34m\]user\[\033[00m\] >", "\[\]\[\]\[\]", "\[\] hi \[hi\] \[\] hello"]:
      self.assertEqual(self.p.EvalPrompt(value.Str(prompt_str)),
          prompt_str.replace("\[", "\x01").replace("\]", "\x02"))

  def testInvalidEscapes(self):
    for invalid_prompt in ["\[\[", "\[\]\[\]\]", "\]\]", "almost valid \]", "\[almost valid"]:
      tokens = list(match.PS1_LEXER.Tokens(invalid_prompt))
      self.assertEqual(prompt.PROMPT_ERROR, self.p._ReplaceBackslashCodes(tokens))

if __name__ == '__main__':
  unittest.main()
