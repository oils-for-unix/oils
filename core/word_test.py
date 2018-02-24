#!/usr/bin/env python
from __future__ import print_function
"""
word_test.py: Tests for word.py
"""

import unittest

from core import word  # module under test


class WordTest(unittest.TestCase):

  def testFoo(self):
    print(word)


if __name__ == '__main__':
  unittest.main()
