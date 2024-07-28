#!/usr/bin/env python2
"""
val_ops_test.py: Tests for val_ops.py
"""
from __future__ import print_function

import unittest

from _devbuild.gen.value_asdl import value
from ysh import val_ops  # module under test


class IteratorTest(unittest.TestCase):

    def testIterator(self):
        a = ['a', 'b']

        it = val_ops.ArrayIter(a)
        self.assertEqual('a', it.FirstValue().s)
        it.Next()

        self.assertEqual('b', it.FirstValue().s)
        it.Next()

        self.assertEqual(None, it.FirstValue())

        mylist = value.List([value.Str('x'), value.Str('y')])

        it = val_ops.ListIterator(mylist)
        self.assertEqual('x', it.FirstValue().s)
        x = it.Next()

        self.assertEqual('y', it.FirstValue().s)
        x = it.Next()

        self.assertEqual(None, it.FirstValue())


if __name__ == '__main__':
    unittest.main()
