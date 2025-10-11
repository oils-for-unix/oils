#!/usr/bin/env python2
"""
trap_osh_test.py: Tests for trap_osh.py
"""
from __future__ import print_function

import unittest

from builtin import trap_osh  # module under test


class TrapTest(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testParse(self):
        cases = [
            ('0', 'EXIT'),
            (' 0 ', None),
            ('EXIT', 'EXIT'),
            ('eXIT', 'EXIT'),
            ('2', 'INT'),
            (' 2 ', None),
            ('iNT', 'INT'),
            ('sIGINT', 'INT'),
            (' 42 ', None),
            ('-150', None),
            ('100000', None),
            ('zzz', None),
        ]
        for user_str, expected in cases:
            print('CASE %r' % user_str)
            parsed_id = trap_osh._ParseSignalOrHook(user_str, None)
            self.assertEqual(expected, parsed_id)


if __name__ == '__main__':
    unittest.main()
