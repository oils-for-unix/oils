#!/usr/bin/env python2
"""
uftrace_allocs_test.py: Tests for uftrace_allocs.py
"""
from __future__ import print_function

import unittest

from benchmarks import uftrace_allocs  # module under test


class PluginTest(unittest.TestCase):

    def testFoo(self):
        s = uftrace_allocs.Stats('_tmp')
        print(s)


if __name__ == '__main__':
    unittest.main()
