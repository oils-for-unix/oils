#!/usr/bin/env python2
"""
builtin_oil_test.py: Tests for builtin_oil.py
"""
from __future__ import print_function

import unittest

import yajl  # test thi stoo

from oil_lang import builtin_oil  # module under test


class JsonTest(unittest.TestCase):

  def testYajl(self):
    print(yajl.dumps({'foo': 42}))

    # Gives us unicode back
    print(yajl.loads('{"bar": 43}'))


if __name__ == '__main__':
  unittest.main()
