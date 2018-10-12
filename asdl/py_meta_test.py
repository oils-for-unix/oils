#!/usr/bin/env python
"""
py_meta_test.py: Tests for py_meta.py
"""
from __future__ import print_function

import unittest

from asdl import py_meta  # module under test

class AsdlTest(unittest.TestCase):

  def testPyMeta(self):
    print(py_meta)


if __name__ == '__main__':
  unittest.main()
