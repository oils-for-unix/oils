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
        self.assertEqual({('Base', 'method'): None, ('Derived', 'method'): ('Base', 'method')},
                         v.virtuals)

        self.assertEqual(True, v.IsVirtual('Base', 'method'))
        self.assertEqual(True, v.IsVirtual('Derived', 'method'))
        self.assertEqual(False, v.IsVirtual('Derived', 'y'))

        self.assertEqual(False, v.IsVirtual('Klass', 'z'))

        self.assertEqual(True, v.HasVTable('Base'))
        self.assertEqual(True, v.HasVTable('Derived'))

        self.assertEqual(False, v.HasVTable('Klass'))

    def testNoInit(self):
        v = pass_state.Virtual()
        v.OnMethod('Base', '__init__')
        v.OnSubclass('Base', 'Derived')
        v.OnMethod('Derived', '__init__')
        v.Calculate()
        self.assertEqual(False, v.HasVTable('Base'))
        self.assertEqual(False, v.HasVTable('Derived'))

    def testCanReorderFields(self):
        """
    class Base(object):
      def __init__(self):
        self.s = ''  # pointer
        self.i = 42

    class Derived(Base):
      def __init__(self):
        Base.__init__()
        self.mylist = []  # type: List[str]

    Note: we can't reorder these, even though there are no virtual methods.
    """
        v = pass_state.Virtual()
        v.OnSubclass('Base2', 'Derived2')
        v.Calculate()

        self.assertEqual(False, v.CanReorderFields('Base2'))
        self.assertEqual(False, v.CanReorderFields('Derived2'))

        self.assertEqual(True, v.CanReorderFields('Klass2'))


class CallGraphTest(unittest.TestCase):

    def testCallGraph(self):
        g = pass_state.CallGraph()

        g.OnCall('a', 'b')
        g.OnCall('b', 'c')
        g.OnCall('b', 'd')
        g.OnCall('d', 'd')
        g.OnCall('e', 'f')

        self.assertEqual(True, g.PathExists('a', 'b'))
        self.assertEqual(True, g.PathExists('a', 'c'))
        self.assertEqual(True, g.PathExists('a', 'd'))
        self.assertEqual(True, g.PathExists('b', 'c'))
        self.assertEqual(True, g.PathExists('b', 'd'))
        self.assertEqual(True, g.PathExists('d', 'd'))
        self.assertEqual(True, g.PathExists('e', 'f'))

        self.assertEqual(True, g.PathExists('a', 'a'))

        self.assertEqual(False, g.PathExists('b', 'a'))
        self.assertEqual(False, g.PathExists('c', 'a'))
        self.assertEqual(False, g.PathExists('d', 'a'))
        self.assertEqual(False, g.PathExists('e', 'a'))
        self.assertEqual(False, g.PathExists('f', 'a'))
        self.assertEqual(False, g.PathExists('c', 'b'))
        self.assertEqual(False, g.PathExists('d', 'b'))
        self.assertEqual(False, g.PathExists('e', 'b'))
        self.assertEqual(False, g.PathExists('d', 'c'))


if __name__ == '__main__':
    unittest.main()
