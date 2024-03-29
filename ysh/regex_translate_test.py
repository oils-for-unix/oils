#!/usr/bin/env python2
from __future__ import print_function

import unittest

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import EggexFlag

from core import error
from core.test_lib import FakeTok
from ysh import regex_translate


def _Name(s):
    # Doesn't work
    return FakeTok(Id.Expr_Name, s)


class RegexTranslateTest(unittest.TestCase):

    def testCanonicalFlags(self):
        reg_icase = _Name('reg_icase')
        i = _Name('i')  # abbreviation
        reg_newline = _Name('reg_newline')
        bad = _Name('bad')

        flags = [EggexFlag(False, reg_icase)]
        self.assertEqual('i', regex_translate.CanonicalFlags(flags))

        flags = [EggexFlag(False, i)]
        self.assertEqual('i', regex_translate.CanonicalFlags(flags))

        flags = [EggexFlag(False, bad)]
        try:
            regex_translate.CanonicalFlags(flags)
        except error.Parse as e:
            print(e.UserErrorString())
        else:
            self.fail('Should have failed')

        order1 = [EggexFlag(False, reg_icase), EggexFlag(False, reg_newline)]
        order2 = [EggexFlag(False, reg_newline), EggexFlag(False, reg_icase)]

        self.assertEqual('in', regex_translate.CanonicalFlags(order1))
        self.assertEqual('in', regex_translate.CanonicalFlags(order2))


if __name__ == '__main__':
    unittest.main()
