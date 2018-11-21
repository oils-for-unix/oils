#!/usr/bin/python -S
"""
oil_parse_test.py: Tests for oil_parse.py
"""
from __future__ import print_function

import unittest

from core import test_lib


class OilParseTest(unittest.TestCase):

  # TODO: Maybe use the osh2oil tool on configure?  And then feed that as a
  # case?
  #
  # That could be part of 'wild'?  Or oil-wild?
  def testSimple(self):
    _, c_parser = test_lib.InitOilParser('echo hi')
    node = c_parser.ParseLogicalLine()
    print(node)


if __name__ == '__main__':
  unittest.main()
