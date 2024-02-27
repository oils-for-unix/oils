#!/usr/bin/env python2
"""
mops_test.py
"""
from __future__ import print_function

import unittest

from mycpp import mops  # module under test


class MopsTest(unittest.TestCase):

    def testBadOps(self):
        i = mops.BigInt(1)
        j = mops.BigInt(2)

        #print(i + j)
        #print(i <= j)

        #print(-i)

        try:
            print(i == j)
        except AssertionError:
            pass
        else:
            self.fail('Expected error')


if __name__ == '__main__':
    unittest.main()
