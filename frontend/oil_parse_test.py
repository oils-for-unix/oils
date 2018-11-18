#!/usr/bin/python -S
"""
oil_parse_test.py: Tests for oil_parse.py
"""
from __future__ import print_function

import unittest

from core import test_lib
from frontend import oil_parse  # module under test


class OilParseTest(unittest.TestCase):
  def setUp(self):
    pass

  def tearDown(self):
    pass

  def testSimple(self):
    _, c_parser = test_lib.InitOilParser('echo hi')
    node = c_parser.ParseLogicalLine()
    print(node)


if __name__ == '__main__':
  unittest.main()
