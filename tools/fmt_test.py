#!/usr/bin/env python2
"""
fmt_test.py
"""

import unittest

from tools import fmt # module under test


class FmtTest(unittest.TestCase):

    def testFoo(self):
        print(fmt)


if __name__ == '__main__':
    unittest.main()
