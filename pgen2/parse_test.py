#!/usr/bin/env python2
"""
parse_test.py: Tests for parse.py
"""
from __future__ import print_function

import unittest

from opy.pgen2 import parse  # module under test


class ParseTest(unittest.TestCase):

  def testPNode(self):
    pnode = parse.PNode(42, ('val', 'prefix', (5, 80)), None)
    print(pnode)

    pnode = parse.PNode(42, ('val', 'prefix', ('1', '2')), [])
    print(pnode)


if __name__ == '__main__':
  unittest.main()
