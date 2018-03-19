#!/usr/bin/python -S
from __future__ import print_function
"""
pyassem_test.py: Tests for pyassem.py
"""

import unittest

# TODO: This import breaks unit test discovery.
#from compiler2 import pyassem  # module under test


class PyAssemTest(unittest.TestCase):

  def setUp(self):
    pass

  def tearDown(self):
    pass

  def testFoo(self):
    return
    g = pyassem.FlowGraph()
    print(g)


if __name__ == '__main__':
  unittest.main()
