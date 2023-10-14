#!/usr/bin/env python2
"""
lexer_test.py: Tests for lexer.py
"""

import unittest

from _devbuild.gen.id_kind_asdl import Id, Id_str
from _devbuild.gen.types_asdl import lex_mode_e
from core import test_lib
from core.test_lib import Tok
from mycpp.mylib import log
from frontend.lexer_def import LEXER_DEF
from frontend import reader


def _PrintfOuterTokens(fmt):
    log('PrintfOuter lexing %r', fmt)

    parse_ctx = test_lib.InitParseContext()
    arena = test_lib.MakeArena('<lexer_test.py>')
    line_reader = reader.StringLineReader(fmt, arena)
    lexer = parse_ctx.MakeLexer(line_reader)

    while True:
        t = lexer.Read(lex_mode_e.PrintfOuter)
        print(t)
        if t.id in (Id.Eof_Real, Id.Eol_Tok):
            break

    log('')


def _PrintToken(t):
    #print(t)
    print('%20s %r' % (Id_str(t.id), t.tval))


def _PrintAllTokens(lx, lex_mode):
    while True:
        t = lx.Read(lex_mode)
        _PrintToken(t)
        if t.id in (Id.Eof_Real, Id.Eol_Tok):
            break


class TokenTest(unittest.TestCase):

    def testToken(self):
        t = Tok(Id.Lit_Chars, 'abc')
        print(t)

        # This redundancy is OK I guess.
        t = Tok(Id.Lit_LBrace, '{')
        print(t)

        t = Tok(Id.Op_Semi, ';')
        print(t)

    def testPrintStats(self):
        states = sorted(LEXER_DEF.items(),
                        key=lambda pair: len(pair[1]),
                        reverse=True)
        total = 0
        for state, re_list in states:
            n = len(re_list)
            print(n, state)
            total += n

        print("Number of lex states: %d" % len(LEXER_DEF))
        print("Number of token dispatches: %d" % total)

    def testMoveToNextLine(self):
        """Test that it doesn't mess up invariants."""
        arena = test_lib.MakeArena('<lexer_test.py>')
        code_str = '''cd {
}'''

        print('=== Printing all tokens')
        if 1:
            _, lx = test_lib.InitLexer(code_str, arena)
            _PrintAllTokens(lx, lex_mode_e.ShCommand)

        print()
        print('=== MoveToNextLine() and LookAheadOne()')
        _, lx = test_lib.InitLexer(code_str, arena)

        t = lx.Read(lex_mode_e.ShCommand)
        _PrintToken(t)
        self.assertEqual(Id.Lit_Chars, t.id)

        t = lx.Read(lex_mode_e.ShCommand)
        _PrintToken(t)
        self.assertEqual(Id.WS_Space, t.id)

        t = lx.Read(lex_mode_e.ShCommand)
        _PrintToken(t)
        self.assertEqual(Id.Lit_LBrace, t.id)

        try:
            lx.MoveToNextLine()
        except AssertionError:
            pass
        else:
            self.fail('Should have asserted')

        t = lx.Read(lex_mode_e.ShCommand)
        _PrintToken(t)
        self.assertEqual(Id.Op_Newline, t.id)

        look_ahead_id = lx.LookAheadOne(lex_mode_e.ShCommand)
        self.assertEqual(Id.Unknown_Tok, look_ahead_id)

        # Method being tested
        lx.MoveToNextLine()

        # Lookahead
        print('Lookahead')
        look_ahead_id = lx.LookAheadOne(lex_mode_e.ShCommand)
        self.assertEqual(Id.Lit_RBrace, look_ahead_id)

        # Lookahead again
        print('Lookahead 2')
        look_ahead_id = lx.LookAheadOne(lex_mode_e.ShCommand)
        self.assertEqual(Id.Lit_RBrace, look_ahead_id)

        t = lx.Read(lex_mode_e.ShCommand)
        _PrintToken(t)
        self.assertEqual(Id.Lit_RBrace, t.id)

        t = lx.Read(lex_mode_e.ShCommand)
        _PrintToken(t)
        self.assertEqual(Id.Eof_Real, t.id)

    def testMaybeUnreadOne(self):
        arena = test_lib.MakeArena('<lexer_test.py>')
        _, lx = test_lib.InitLexer('()', arena)

        t = lx.Read(lex_mode_e.ShCommand)
        print(t)
        self.assertEqual(Id.Op_LParen, t.id)

        t = lx.Read(lex_mode_e.ShCommand)
        print(t)
        self.assertEqual(Id.Op_RParen, t.id)

        # Go back
        lx.MaybeUnreadOne()

        # Push Hint
        lx.PushHint(Id.Op_RParen, Id.Right_CasePat)

        # Now we see it again another a Id
        t = lx.Read(lex_mode_e.ShCommand)
        print(t)
        self.assertEqual(Id.Right_CasePat, t.id)

    def testPrintf(self):
        # Demonstrate input handling quirk

        # Get Id.Eof_Real because len('') == 0
        _PrintfOuterTokens('')

        # Get Id.Eol_Tok because len('\0') == 1
        _PrintfOuterTokens('\0')

        # Get x, then Id.Eof_Real because there are no more lines
        _PrintfOuterTokens('x\0')


if __name__ == '__main__':
    unittest.main()
