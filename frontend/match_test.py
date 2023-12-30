#!/usr/bin/env python2
"""
match_test.py: Tests for match.py
"""
from __future__ import print_function

import unittest

from _devbuild.gen.id_kind_asdl import Id, Id_str
from mycpp.mylib import log
from frontend import match  # module under test


def _PrintTokens(lex):
    for id_, val in lex.Tokens():
        log('    %s %r', Id_str(id_), val)
        if id_ == Id.Eol_Tok:
            break


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
        _PrintTokens(lex)

    def testJ8Lexer(self):
        cases = [
            '00',
            '[]',
            '[3.14, 4, true]',
            'truez',
            'false\t',
            'bad',
        ]

        for s in cases:
            log('---')
            log('J8 CASE %r', s)
            lex = match.SimpleLexer(match.MatchJ8Token, s)
            _PrintTokens(lex)

    def testJ8StrLexer(self):
        cases = [
            '"hi"',
            # Newlines in strings are control chars, not accepted
            '"hi\n"',
            '"hi\\n"',
            r'"\yff \xff \u1234 \u{123456} \\ \" "',

            # This points at \ as Id.Unknown_Tok, which I suppose is OK
            r'"\a \z \/ \b "',
        ]

        for s in cases:
            log('---')
            log('J8 STR CASE %r', s)
            lex = match.SimpleLexer(match.MatchJ8StrToken, s)
            _PrintTokens(lex)

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
