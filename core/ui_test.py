#!/usr/bin/python -S
from __future__ import print_function
"""
ui_test.py: Tests for ui.py
"""

import unittest

from core import ui  # module under test


class UiTest(unittest.TestCase):

  def testFoo(self):
    ui.usage('oops')


if __name__ == '__main__':
  unittest.main()
