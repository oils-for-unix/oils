#!/usr/bin/env python2
from __future__ import print_function

import unittest

from _devbuild.gen.syntax_asdl import loc
from core import error
from mycpp import mops
from osh import sh_expr_eval


class ParsingTest(unittest.TestCase):

    def checkCases(self, cases):
        for s, expected in cases:
            try:
                err, actual = sh_expr_eval._MaybeParseInt(s, loc.Missing)
            except error.Strict:
                err = True

            if err:
                actual = None

            #print(expected and expected.i, actual and actual.i)
            self.assertEqual(expected, actual)

    def testDecimalConst(self):
        CASES = [
            ('0', mops.BigInt(0)),
            ('42042', mops.BigInt(42042)),
            (' 2 ', mops.BigInt(2)),
            (' 2\t', mops.BigInt(2)),
            ('\r\n2\r\n', mops.BigInt(2)),
            ('1F', None),
            ('011', mops.BigInt(9)),  # Parsed as an octal
            ('1_1', None),
            ('1 1', None),
        ]
        self.checkCases(CASES)

    def testOctalConst(self):
        CASES = [
            ('0777', mops.BigInt(511)),
            ('00012', mops.BigInt(10)),
            (' 010\t', mops.BigInt(8)),
            ('\n010\r\n', mops.BigInt(8)),
            ('019', None),
            ('0_9', None),
            ('0 9', None),
            ('0F0', None),
        ]
        self.checkCases(CASES)

    def testHexConst(self):
        CASES = [
            ('0xFF', mops.BigInt(255)),
            ('0xff', mops.BigInt(255)),
            ('0x0010', mops.BigInt(16)),
            (' 0x1A ', mops.BigInt(26)),
            ('\t0x1A\r\n', mops.BigInt(26)),
            ('FF', None),
            ('0xG', None),
            ('0x1_0', None),
            ('0x1 0', None),
            ('0X12', None),
        ]
        self.checkCases(CASES)

    def testArbitraryBaseConst(self):
        CASES = [
            ('2#0110', mops.BigInt(6)),
            ('8#777', mops.BigInt(511)),
            ('16#ff', mops.BigInt(255)),
            (' 16#ff\r  ', mops.BigInt(255)),
            ('\t16#ff\n', mops.BigInt(255)),
            ('64#123abcABC@_', mops.BigInt(1189839476434038719)),
            ('16#FF', None),  # F != f, so F is out of range of the base
            ('010#42', None),  # Base cannot start with 0
            ('65#1', None),  # Base too large
            ('0#1', None),  # Base too small
            ('1#1', None),  # Base too small
        ]
        self.checkCases(CASES)


if __name__ == '__main__':
    unittest.main()
