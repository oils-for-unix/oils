#!/usr/bin/env python2
"""
consts_test.py: Tests for consts.py
"""

import unittest

import consts  # module under test


class ConstsTest(unittest.TestCase):

  def testFoo(self):
    self.assertEqual(consts.CO_OPTIMIZED, 0x0001)
    self.assertEqual(consts.CO_NEWLOCALS, 0x0002)
    self.assertEqual(consts.CO_VARARGS, 0x0004)
    self.assertEqual(consts.CO_VARKEYWORDS, 0x0008)
    self.assertEqual(consts.CO_NESTED, 0x0010)
    self.assertEqual(consts.CO_GENERATOR, 0x0020)

    self.assertEqual(consts.CO_FUTURE_DIVISION, 0x2000)
    self.assertEqual(consts.CO_FUTURE_ABSIMPORT, 0x4000)
    self.assertEqual(consts.CO_FUTURE_WITH_STATEMENT, 0x8000)
    self.assertEqual(consts.CO_FUTURE_PRINT_FUNCTION, 0x10000)


if __name__ == '__main__':
  unittest.main()
