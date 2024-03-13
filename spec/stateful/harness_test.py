#!/usr/bin/env python3
"""
harness_test.py: Tests for harness.py
"""
from __future__ import print_function

import sys
import unittest

import harness  # module under test


class HarnessTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testPrintResults(self):
        Result = harness.Result

        shell_pairs = [
            ('osh', 'bin/osh'),
            ('bash', 'bash'),
            ('dash', 'dash'),
        ]
        result_table = [
            [0, Result.OK, Result.OK, Result.OK, 'first'],
            [1, Result.FAIL, Result.OK, Result.OK, 'second'],
        ]
        flaky = {
            (0, 'bash'): -1,
            (0, 'osh'): -1,
            (0, 'dash'): -1,
            (1, 'osh'): 2,
            (1, 'bash'): 1,
            (1, 'dash'): -1,
        }

        harness.PrintResults(shell_pairs, result_table, flaky, 4, sys.stdout)


if __name__ == '__main__':
    unittest.main()
