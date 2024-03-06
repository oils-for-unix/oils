#!/usr/bin/env python2
"""
pretty_test.py
"""

import unittest

from data_lang import pretty  # module under test


class PrettyTest(unittest.TestCase):

    def testFoo(self):
        print(pretty)


if __name__ == '__main__':
    unittest.main()
