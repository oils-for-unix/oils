#!/usr/bin/env python2
"""
tea_eval_test.py: Tests for tea_eval.py
"""
from __future__ import print_function

import unittest

from tea import tea_eval  # module under test


class TeaEvalTest(unittest.TestCase):

  def testTea(self):
    tea_ev = tea_eval.TeaEvaluator()
    print(tea_ev)


if __name__ == '__main__':
  unittest.main()
