#!/usr/bin/env python3
"""
pass_state_test.py: Tests for pass_state.py
"""
from __future__ import print_function

import unittest

import pass_state  # module under test


class VirtualTest(unittest.TestCase):

  def testVirtual(self):
    """
    Example:

    class Base(object):
      def method(self):  # we don't know if this is virtual yet
        pass
      def x(self):
        pass

    class Derived(Base):
      def method(self):  # now it's virtual!
        pass
      def y(self):
        pass
    """
    v = pass_state.Virtual()
    v.OnMethod('Base', 'method')
    v.OnMethod('Base', 'x')
    v.OnSubclass('Base', 'Derived')
    v.OnMethod('Derived', 'method')
    v.OnMethod('Derived', 'y')

    v.Calculate()

    print(v.virtuals)
    self.assertEqual(
        [('Base', 'method'), ('Derived', 'method')],
        v.virtuals)

    self.assertEqual(True, v.IsVirtual('Base', 'method'))
    self.assertEqual(True, v.IsVirtual('Derived', 'method'))
    self.assertEqual(False, v.IsVirtual('Derived', 'y'))


if __name__ == '__main__':
  unittest.main()
