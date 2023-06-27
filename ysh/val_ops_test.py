#!/usr/bin/env python2
"""
val_ops_test.py: Tests for val_ops.py
"""
from __future__ import print_function

import unittest

from _devbuild.gen.runtime_asdl import value
from ysh import val_ops  # module under test


class IteratorTest(unittest.TestCase):

    def testItemIterator(self):
        a = value.MaybeStrArray(['a', 'b'])

        it = val_ops.ItemIterator(a)
        x = it.GetNext()
        y = it.GetNext()
        z = it.GetNext()

        self.assertEqual('a', x.s)
        self.assertEqual('b', y.s)
        self.assertEqual(None, z)

        a = value.List([value.Str('x'), value.Str('y')])

        it = val_ops.ItemIterator(a)
        x = it.GetNext()
        y = it.GetNext()
        z = it.GetNext()

        self.assertEqual('x', x.s)
        self.assertEqual('y', y.s)
        self.assertEqual(None, z)


if __name__ == '__main__':
    unittest.main()
