#!/usr/bin/env python2
"""
mylib_test.py: Tests for mylib.py
"""
from __future__ import print_function

import unittest

from mycpp import mylib  # module under test


class MylibTest(unittest.TestCase):

    def testSplit(self):
        self.assertEqual(('foo', None), mylib.split_once('foo', '='))
        self.assertEqual(('foo', ''), mylib.split_once('foo=', '='))
        self.assertEqual(('foo', 'bar'), mylib.split_once('foo=bar', '='))

    def testFile(self):
        return
        stdout = mylib.File(1)
        stderr = mylib.File(2)

        stdout.write('stdout ')
        stdout.writeln('stdout')

        stderr.write('stderr ')
        stderr.writeln('stderr ')

    def testUniqueObjects(self):
        u = mylib.UniqueObjects()

        foo = 'foo'
        bar = 'bar'
        d = {}

        u.Add(foo)
        u.Add(bar)
        u.Add(d)

        self.assertEqual(0, u.Get(foo))
        self.assertEqual(1, u.Get(bar))
        self.assertEqual(2, u.Get(d))
        self.assertEqual(-1, u.Get('zzz'))

        # Can't add it twice, caller is responsible for checking
        try:
            u.Add(foo)
        except AssertionError:
            pass
        else:
            self.fail('Expected assertion')


if __name__ == '__main__':
    unittest.main()
