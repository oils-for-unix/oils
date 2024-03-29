#!/usr/bin/env python2
"""
lexer_def_test.py: Tests for lexer_def.py
"""
from __future__ import print_function

import re
import unittest

from _devbuild.gen.id_kind_asdl import Id, Id_str, Kind
from _devbuild.gen.types_asdl import lex_mode_e
from core import test_lib
from core.test_lib import FakeTok
from mycpp.mylib import log
from frontend import lexer
from frontend import lexer_def
from frontend import consts
from frontend import match

_ = log


def _InitLexer(s):
    arena = test_lib.MakeArena('<lex_test.py>')
    _, lexer = test_lib.InitLexer(s, arena)
    return lexer


class AsdlTest(unittest.TestCase):

    def testLexMode(self):
        print(lex_mode_e.DQ)


CMD = """\
ls /
ls /home/
"""


class LexerTest(unittest.TestCase):

    def assertTokensEqual(self, left, right):
        self.assertTrue(test_lib.TokensEqual(left, right),
                        'Expected %r, got %r' % (left, right))

    def testRead(self):
        lexer = _InitLexer(CMD)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Lit_Chars, 'ls'), t)
        t = lexer.Read(lex_mode_e.ShCommand)

        self.assertTokensEqual(FakeTok(Id.WS_Space, ' '), t)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Lit_Slash, '/'), t)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Op_Newline, '\n'), t)

        # Line two
        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Lit_Chars, 'ls'), t)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.WS_Space, ' '), t)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Lit_Slash, '/'), t)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Lit_Chars, 'home'), t)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Lit_Slash, '/'), t)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Op_Newline, '\n'), t)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Eof_Real, ''), t)

        # Another EOF gives EOF
        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Eof_Real, ''), t)

    def testMode_VSub_ArgUnquoted(self):
        # Another EOF gives EOF
        lx = _InitLexer("'hi'")
        t = lx.Read(lex_mode_e.VSub_ArgUnquoted)
        print(t)

        self.assertTokensEqual(FakeTok(Id.Left_SingleQuote, "'"), t)

        lx = _InitLexer("~root")
        t = lx.Read(lex_mode_e.VSub_ArgUnquoted)
        print(t)

        self.assertTokensEqual(FakeTok(Id.Lit_Tilde, '~'), t)

    def testMode_ExtGlob(self):
        lexer = _InitLexer('@(foo|bar)')

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.ExtGlob_At, '@('), t)

        t = lexer.Read(lex_mode_e.ExtGlob)
        self.assertTokensEqual(FakeTok(Id.Lit_Chars, 'foo'), t)

        t = lexer.Read(lex_mode_e.ExtGlob)
        self.assertTokensEqual(FakeTok(Id.Op_Pipe, '|'), t)

        t = lexer.Read(lex_mode_e.ExtGlob)
        self.assertTokensEqual(FakeTok(Id.Lit_Chars, 'bar'), t)

        t = lexer.Read(lex_mode_e.ExtGlob)
        self.assertTokensEqual(FakeTok(Id.Op_RParen, ')'), t)

        # Individual cases

        lexer = _InitLexer('@(')
        t = lexer.Read(lex_mode_e.ExtGlob)
        self.assertTokensEqual(FakeTok(Id.ExtGlob_At, '@('), t)

        lexer = _InitLexer('*(')
        t = lexer.Read(lex_mode_e.ExtGlob)
        self.assertTokensEqual(FakeTok(Id.ExtGlob_Star, '*('), t)

        lexer = _InitLexer('?(')
        t = lexer.Read(lex_mode_e.ExtGlob)
        self.assertTokensEqual(FakeTok(Id.ExtGlob_QMark, '?('), t)

        lexer = _InitLexer('$')
        t = lexer.Read(lex_mode_e.ExtGlob)
        self.assertTokensEqual(FakeTok(Id.Lit_Other, '$'), t)

    def testMode_BashRegex(self):
        lexer = _InitLexer('(foo|bar)')

        t = lexer.Read(lex_mode_e.BashRegex)
        self.assertTokensEqual(FakeTok(Id.Lit_Other, '('), t)

        t = lexer.Read(lex_mode_e.BashRegex)
        self.assertTokensEqual(FakeTok(Id.Lit_Chars, 'foo'), t)

        t = lexer.Read(lex_mode_e.BashRegex)
        self.assertTokensEqual(FakeTok(Id.Lit_Other, '|'), t)

    def testMode_DBracket(self):
        lex = _InitLexer('-z foo')
        t = lex.Read(lex_mode_e.DBracket)
        self.assertTokensEqual(FakeTok(Id.BoolUnary_z, '-z'), t)
        self.assertEqual(Kind.BoolUnary, consts.GetKind(t.id))

    def testMode_DollarSq(self):
        lexer = _InitLexer(r'foo bar\n \x00 \000 \u0065')

        t = lexer.Read(lex_mode_e.SQ_C)
        print(t)
        self.assertTokensEqual(FakeTok(Id.Lit_Chars, 'foo bar'), t)

        t = lexer.Read(lex_mode_e.SQ_C)
        print(t)
        self.assertTokensEqual(FakeTok(Id.Char_OneChar, r'\n'), t)

    def testMode_Backtick(self):
        CASES = [
            r'echo \" \\ hi`',
            r'`',
            r'',
        ]

        for case in CASES:
            print()
            print('--- %s ---' % case)
            print()

            lexer = _InitLexer(case)

            while True:
                t = lexer.Read(lex_mode_e.Backtick)
                print(t)
                if t.id == Id.Eof_Real:
                    break

    def testMode_Printf(self):
        CASES = [
            r'hello %s\n',
            r'%% percent %%\377',
        ]

        for case in CASES:
            print()
            print('--- %s ---' % case)
            print()

            lexer = _InitLexer(case)

            while True:
                t = lexer.Read(lex_mode_e.PrintfOuter)
                print(t)
                if t.id == Id.Eof_Real:
                    break

        # Now test the Printf_Percent mode
        CASES = [r'-3.3f', r'03d']

        for case in CASES:
            print()
            print('--- %s ---' % case)
            print()

            lexer = _InitLexer(case)

            while True:
                t = lexer.Read(lex_mode_e.PrintfPercent)
                print(t)
                if t.id == Id.Eof_Real:
                    break

    def testMode_Expr(self):
        CASES = [
            r'@[ ]',
        ]

        for case in CASES:
            print()
            print('--- %s ---' % case)
            print()

            lexer = _InitLexer(case)

            while True:
                t = lexer.Read(lex_mode_e.Expr)
                print(t)
                if t.id == Id.Eof_Real:
                    break

    def testLookPastSpace(self):
        # I think this is the usage pattern we care about.  Peek and Next() past
        # the function; then Peek() the next token.  Then Lookahead in that state.
        lexer = _InitLexer('fun()')

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Lit_Chars, 'fun'), t)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Op_LParen, '('), t)

        self.assertEqual(Id.Op_RParen,
                         lexer.LookPastSpace(lex_mode_e.ShCommand))

        lexer = _InitLexer('fun ()')

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Lit_Chars, 'fun'), t)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.WS_Space, ' '), t)

        self.assertEqual(Id.Op_LParen,
                         lexer.LookPastSpace(lex_mode_e.ShCommand))

    def testPushHint(self):
        # Extglob use case
        lexer = _InitLexer('@()')
        lexer.PushHint(Id.Op_RParen, Id.Right_ExtGlob)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.ExtGlob_At, '@('), t)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Right_ExtGlob, ')'), t)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Eof_Real, ''), t)

    def testEmitCompDummy(self):
        lexer = _InitLexer('echo ')
        lexer.EmitCompDummy()

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Lit_Chars, 'echo'), t)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.WS_Space, ' '), t)

        # Right before EOF
        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Lit_CompDummy, ''), t)

        t = lexer.Read(lex_mode_e.ShCommand)
        self.assertTokensEqual(FakeTok(Id.Eof_Real, ''), t)


class LineLexerTest(unittest.TestCase):

    def setUp(self):
        self.arena = test_lib.MakeArena('<lex_test.py>')

    def assertTokensEqual(self, left, right):
        #log('LEFT %s', left)
        #log('RIGHT %s', right)
        # self.assertTrue(test_lib.TokensEqual(left, right))
        self.assertEqual(left.id, right.id,
                         '%s != %s' % (Id_str(left.id), Id_str(right.id)))
        #self.assertEqual(left.tval, right.tval)

    def testReadOuter(self):
        l = test_lib.InitLineLexer('\n', self.arena)
        self.assertTokensEqual(lexer.DummyToken(Id.Op_Newline, None),
                               l.Read(lex_mode_e.ShCommand))

    def testRead_VSub_ArgUnquoted(self):
        l = test_lib.InitLineLexer("'hi'", self.arena)
        t = l.Read(lex_mode_e.VSub_ArgUnquoted)
        self.assertEqual(Id.Left_SingleQuote, t.id)

    def testLookPastSpace(self):
        # Lines always end with '\n'
        l = test_lib.InitLineLexer('', self.arena)
        self.assertEqual(Id.Unknown_Tok, l.LookPastSpace(lex_mode_e.ShCommand))

        l = test_lib.InitLineLexer('foo', self.arena)
        self.assertTokensEqual(FakeTok(Id.Lit_Chars, 'foo'),
                               l.Read(lex_mode_e.ShCommand))
        self.assertEqual(Id.Unknown_Tok, l.LookPastSpace(lex_mode_e.ShCommand))

        l = test_lib.InitLineLexer('foo  bar', self.arena)
        self.assertTokensEqual(FakeTok(Id.Lit_Chars, 'foo'),
                               l.Read(lex_mode_e.ShCommand))
        self.assertEqual(Id.Lit_Chars, l.LookPastSpace(lex_mode_e.ShCommand))

        # No lookahead; using the cursor!
        l = test_lib.InitLineLexer('fun(', self.arena)
        self.assertTokensEqual(FakeTok(Id.Lit_Chars, 'fun'),
                               l.Read(lex_mode_e.ShCommand))
        self.assertEqual(Id.Op_LParen, l.LookPastSpace(lex_mode_e.ShCommand))

        l = test_lib.InitLineLexer('fun  (', self.arena)
        self.assertTokensEqual(FakeTok(Id.Lit_Chars, 'fun'),
                               l.Read(lex_mode_e.ShCommand))
        self.assertEqual(Id.Op_LParen, l.LookPastSpace(lex_mode_e.ShCommand))


class RegexTest(unittest.TestCase):

    def testNul(self):
        nul_pat = re.compile(r'[\0]')
        self.assertEqual(False, bool(nul_pat.match('x')))
        self.assertEqual(True, bool(nul_pat.match('\0')))

        _, p, _ = lexer_def.ECHO_E_DEF[-1]
        print('P %r' % p)
        last_echo_e_pat = re.compile(p)
        self.assertEqual(True, bool(last_echo_e_pat.match('x')))
        self.assertEqual(False, bool(last_echo_e_pat.match('\0')))


class OtherLexerTest(unittest.TestCase):

    def testEchoLexer(self):
        CASES = [
            r'newline \n NUL \0 octal \0377 hex \x00',
            r'unicode \u0065 \U00000065',
            r'\d \e \f \g',
        ]
        for s in CASES:
            lex = match.EchoLexer(s)
            print(lex.Tokens())

    def testPS1Lexer(self):
        print(list(match.Ps1Tokens(r'foo')))
        print(list(match.Ps1Tokens(r'\h \w \$')))

    def testHistoryLexer(self):
        print(list(match.HistoryTokens(r'echo hi')))

        print(list(match.HistoryTokens(r'echo !! !* !^ !$')))

        # No history operator with \ escape
        tokens = list(match.HistoryTokens(r'echo \!!'))
        print(tokens)
        self.assert_(Id.History_Op not in [tok_type for tok_type, _ in tokens])

        print(list(match.HistoryTokens(r'echo !3...')))
        print(list(match.HistoryTokens(r'echo !-5...')))
        print(list(match.HistoryTokens(r'echo !x/foo.py bar')))

        print('---')

        # No history operator in single quotes
        tokens = list(match.HistoryTokens(r"echo '!!' $'!!' "))
        print(tokens)
        self.assert_(Id.History_Op not in [tok_type for tok_type, _ in tokens])

        # No history operator in incomplete single quotes
        tokens = list(match.HistoryTokens(r"echo '!! "))
        print(tokens)
        self.assert_(Id.History_Op not in [tok_type for tok_type, _ in tokens])

        # Quoted single quote, and then a History operator
        tokens = list(match.HistoryTokens(r"echo \' !! "))
        print(tokens)
        # YES operator
        self.assert_(Id.History_Op in [tok_type for tok_type, _ in tokens])

    def testHistoryDoesNotConflict(self):
        # https://github.com/oilshell/oil/issues/264
        #
        # Bash has a bunch of hacks to suppress the conflict between ! for history
        # and:
        #
        # 1. [!abc] globbing
        # 2. ${!foo} indirect expansion
        # 3. $!x -- the PID
        # 4. !(foo|bar) -- extended glob
        #
        # I guess [[ a != b ]] doesn't match the pattern in bash.

        three_other = [Id.History_Other, Id.History_Other, Id.History_Other]
        two_other = [Id.History_Other, Id.History_Other]
        CASES = [
            (r'[!abc]', three_other),
            (r'${!indirect}', three_other),
            (r'$!x', three_other),  # didn't need a special case
            (r'!(foo|bar)', two_other),  # didn't need a special case
        ]

        for s, expected_types in CASES:
            tokens = list(match.HistoryTokens(s))
            print(tokens)
            actual_types = [id_ for id_, val in tokens]

            self.assert_(Id.History_Search not in actual_types, tokens)

            self.assertEqual(expected_types, actual_types)

    def testBraceRangeLexer(self):
        CASES = [
            'a..z',
            '100..300',
            '-300..-100..1',
            '1.3',  # invalid
            'aa',
        ]
        for s in CASES:
            lex = match.BraceRangeLexer(s)
            print(lex.Tokens())


if __name__ == '__main__':
    unittest.main()
