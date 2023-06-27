#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""util_test.py: Tests for util.py."""

import unittest

from _devbuild.gen.runtime_asdl import value
from core import util  # module under test


class UtilTest(unittest.TestCase):

    def testDebugFile(self):
        n = util.NullDebugFile()
        n.write('foo')


class IteratorTest(unittest.TestCase):

    def testItemIterator(self):
        a = value.MaybeStrArray(['a', 'b'])

        it = util.ItemIterator(a)
        x = it.GetNext()
        y = it.GetNext()
        z = it.GetNext()

        self.assertEqual('a', x.s)
        self.assertEqual('b', y.s)
        self.assertEqual(None, z)

        a = value.List([value.Str('x'), value.Str('y')])

        it = util.ItemIterator(a)
        x = it.GetNext()
        y = it.GetNext()
        z = it.GetNext()

        self.assertEqual('x', x.s)
        self.assertEqual('y', y.s)
        self.assertEqual(None, z)


if __name__ == '__main__':
    unittest.main()
