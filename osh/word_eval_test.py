#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
word_eval_test.py: Tests for word_eval.py
"""
from __future__ import print_function

import unittest

from core import test_lib
from osh.cmd_parse_test import assertParseSimpleCommand
from osh import state
from osh import word_eval  # module under test


def InitEvaluator():
  word_ev = test_lib.MakeTestEvaluator()
  state.SetLocalString(word_ev.mem, 'x', '- -- ---')
  state.SetLocalString(word_ev.mem, 'y', 'y yy yyy')
  state.SetLocalString(word_ev.mem, 'empty', '')
  return word_ev


class WordEvalTest(unittest.TestCase):

  def testEvalWordSequence(self):
    node = assertParseSimpleCommand(self, 'ls foo')
    self.assertEqual(2, len(node.words), node.words)

    ev = InitEvaluator()
    argv = ev.EvalWordSequence(node.words)
    print()
    print(argv)

    node = assertParseSimpleCommand(self, 'ls [$x] $y core/a*.py')
    print(node)
    ev = InitEvaluator()
    argv = ev.EvalWordSequence(node.words)
    print()
    print(argv)


if __name__ == '__main__':
  unittest.main()
