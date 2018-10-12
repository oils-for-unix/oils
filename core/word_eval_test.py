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

from core import word_eval  # module under test


class WordEvalTest(unittest.TestCase):

  def testWordEval(self):
    print(word_eval)


if __name__ == '__main__':
  unittest.main()
