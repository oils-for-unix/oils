#!/usr/bin/env python2
"""
match_test.py: Tests for match.py
"""
from __future__ import print_function

import unittest

from _devbuild.gen.id_kind_asdl import Id, Id_str
from mycpp.mylib import log
from frontend import match  # module under test


class MatchTest(unittest.TestCase):

    def testShouldHijack(self):
        self.assertEqual(False, match.ShouldHijack('# comment\n[line 2]'))
        self.assertEqual(False, match.ShouldHijack('#!/usr/bin/python\n'))
        self.assertEqual(False, match.ShouldHijack(''))
        self.assertEqual(False, match.ShouldHijack('\n'))

        self.assertEqual(True, match.ShouldHijack('#!/usr/bin/env bash\n'))

        self.assertEqual(True, match.ShouldHijack('#!/bin/bash\n[line 2]'))
        self.assertEqual(True, match.ShouldHijack('#!/bin/bash -e\n[line 2]'))
        self.assertEqual(True, match.ShouldHijack('#!/bin/sh\n[line 2]\n'))
        self.assertEqual(True, match.ShouldHijack('#!/bin/sh -e\n[line 2]\n'))

        # Unlikely but OK
        self.assertEqual(True, match.ShouldHijack('#!/usr/bin/env sh\n'))

        # fastlex bug: should not allow \0
        self.assertEqual(False, match.ShouldHijack('#!/usr/bin/env \0 sh\n'))

    def testBraceRangeLexer(self):
        lex = match.BraceRangeLexer('1..3')
        while True:
            id_, val = lex.Next()
            log('%s %r', Id_str(id_), val)
            if id_ == Id.Eol_Tok:
                break

    def testLooksLike(self):
        INTS = [
            (False, ''),
            (False, 'foo'),
            (True, '3'),
            (True, '-3'),
            (False, '-'),
            (False, '.'),
            (True, '\t12 '),
            (True, '\t-12 '),
            (False, ' - 12 '),
        ]

        MORE_INTS = [
            (True, ' 3_000 '),
        ]

        for expected, s in INTS + MORE_INTS:
            self.assertEqual(expected, match.LooksLikeInteger(s))

        FLOATS = [
            (True, '3.0'),
            (True, '-3.0'),
            (True, '\t3.0 '),
            (True, '\t-3.0  '),
            (False, ' - 3.0 '),
        ]

        for expected, s in INTS + FLOATS:  # Use BOTH test cases
            self.assertEqual(expected, match.LooksLikeFloat(s), s)


if __name__ == '__main__':
    unittest.main()
