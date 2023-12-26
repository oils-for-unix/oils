#!/usr/bin/env python2
"""
pyj8_test.py: Tests for pyj8.py
"""
from __future__ import print_function

import unittest

from _devbuild.gen.syntax_asdl import Id, Id_str
from data_lang import pyj8  # module under test
from mycpp.mylib import log


def _PrintTokens(lex):
    log('---')
    log('J8 Case %r', lex.s)
    pos = 0
    while True:
        id_, end_pos, decoded = lex.Next()
        val = lex.s[pos:end_pos]
        log('    %20s %10r %r', Id_str(id_), val, decoded)
        if id_ == Id.Eol_Tok:
            break
        pos = end_pos
    log('')


class J8Test(unittest.TestCase):

    def testEncode(self):
        en = pyj8.EncodeString('hello', 0)
        print(en)

        en = pyj8.EncodeString('\xff-\xfe-\xff-\xfe', 0)
        print(en)

        # multiple errrors
        en = pyj8.EncodeString('hello\xffthere \xfe\xff gah', 0)
        print(en)

        # valid mu
        en = pyj8.EncodeString('hello \xce\xbc there', 0)
        print(en)

        # two first bytes - invalid
        en = pyj8.EncodeString('hello \xce\xce there', 0)
        print(en)

        # two cont bytes - invalid
        en = pyj8.EncodeString('hello \xbc\xbc there', 0)
        print(en)

    def testLexerDecoder(self):
        lex = pyj8.LexerDecoder(r'{"hi": "bye \n"}')
        _PrintTokens(lex)

        lex = pyj8.LexerDecoder(r'{u"unicode": b"bytes \yff"}')
        _PrintTokens(lex)

        lex = pyj8.LexerDecoder(r'{"x": [1, 2, 3.14, true]}')
        _PrintTokens(lex)

        lex = pyj8.LexerDecoder(r'[1e9, 1e-9, -1e9, -1E-9, 42]')
        _PrintTokens(lex)


if __name__ == '__main__':
    unittest.main()

# vim: sw=4
