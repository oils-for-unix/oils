#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
word_parse_test.py: Tests for word_parse.py
"""

import unittest

from _devbuild.gen.id_kind_asdl import Id, Id_str
from _devbuild.gen.syntax_asdl import arith_expr_e, word_e, rhs_word_e
from _devbuild.gen.types_asdl import lex_mode_e

from asdl import format as fmt
from core import error
from core import test_lib
from core.test_lib import FakeTok
from frontend import lexer
from frontend import location
from osh import word_


def _assertReadWordWithArena(test, w_parser):
    w = w_parser.ReadWord(lex_mode_e.ShCommand)
    assert w is not None
    fmt.PrettyPrint(w)
    print('')

    # Next word must be Eof_Real
    w2 = w_parser.ReadWord(lex_mode_e.ShCommand)
    test.assertTrue(test_lib.TokensEqual(FakeTok(Id.Eof_Real, ''), w2), w2)
    return w


def _assertReadWord(test, word_str, oil_at=False):
    print('')
    print('--- %s' % word_str)
    print('')

    arena = test_lib.MakeArena('word_parse_test.py')
    w_parser = test_lib.InitWordParser(word_str, arena=arena, oil_at=oil_at)
    w = _assertReadWordWithArena(test, w_parser)
    return w


def _assertReadWordFailure(test, word_str, oil_at=False):
    print('\n---', word_str)
    w_parser = test_lib.InitWordParser(word_str, oil_at=oil_at)
    try:
        w = w_parser.ReadWord(lex_mode_e.ShCommand)
    except error.Parse as e:
        print('Got expected ParseError: %s' % e)
    else:
        fmt.PrettyPrint(w)
        test.fail('Expected a parser error, got %r' % w)


def _assertSpanForWord(test, word_str):
    arena = test_lib.MakeArena('word_parse_test.py')
    w_parser = test_lib.InitWordParser(word_str, arena=arena)
    w = _assertReadWordWithArena(test, w_parser)
    tok = location.LeftTokenForWord(w)

    print(word_str)
    print(tok)


def _GetSuffixOp(test, w):
    """Get a single transform op."""
    test.assertEqual(1, len(w.parts))
    return w.parts[0].suffix_op


def _GetPrefixOp(test, w):
    """Get a single transform op."""
    test.assertEqual(1, len(w.parts))
    return w.parts[0].prefix_op.id


def _GetVarSub(test, w):
    """Get a single transform op."""
    test.assertEqual(1, len(w.parts))
    return w.parts[0]


class ArenaTest(unittest.TestCase):
    """It's more convenient to test the arena here, because we have a proper
    lexer and so forth."""

    def testSnipCodeString(self):
        expr = """\
hi'
single quoted'"double
quoted
"there
    """

        arena = test_lib.MakeArena('hi')
        w_parser = test_lib.InitWordParser(expr, arena=arena)
        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        print(w)

        left = w.parts[1].left  # left single quote
        right = w.parts[2].right  # right double quote

        s = arena.SnipCodeString(left, right)

        print('s = %r' % s)
        self.assertEqual("""\
'
single quoted'"double
quoted
"\
""", s)

        s = arena.SnipCodeString(w.parts[1].left, w.parts[1].right)

        print('s = %r' % s)
        self.assertEqual("""\
'
single quoted'\
""", s)

        # Just snip one token
        s = arena.SnipCodeString(w.parts[0], w.parts[0])

        print('s = %r' % s)
        self.assertEqual('hi', s)

    def testSaveLinesAndDiscard(self):
        # Also takes a left, right, token
        pass


class LexerTest(unittest.TestCase):
    """It's more convenient to test the lexer here, because we have a proper
    lexer and so forth."""

    def testAssignFunctions(self):
        arena = test_lib.MakeArena('')

        expr = 'ls; foo=42'
        w_parser = test_lib.InitWordParser(expr, arena=arena)

        # Skip first two words
        w_parser.ReadWord(lex_mode_e.ShCommand)
        w_parser.ReadWord(lex_mode_e.ShCommand)
        w3 = w_parser.ReadWord(lex_mode_e.ShCommand)
        print(w3)

        self.assertEqual(False, lexer.IsPlusEquals(w3.parts[0]))
        self.assertEqual('foo', lexer.TokenSliceRight(w3.parts[0], -1))

        expr = 'ls; foo+=X'
        w_parser = test_lib.InitWordParser(expr, arena=arena)

        # Skip first two words
        w_parser.ReadWord(lex_mode_e.ShCommand)
        w_parser.ReadWord(lex_mode_e.ShCommand)
        w3 = w_parser.ReadWord(lex_mode_e.ShCommand)
        print(w3)

        self.assertEqual(True, lexer.IsPlusEquals(w3.parts[0]))
        self.assertEqual('foo', lexer.TokenSliceRight(w3.parts[0], -2))


class WordParserTest(unittest.TestCase):

    def testStaticEvalWord(self):
        expr = r'\EOF'  # Quoted here doc delimiter
        w_parser = test_lib.InitWordParser(expr)
        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        ok, s, quoted = word_.StaticEval(w)
        self.assertEqual(True, ok)
        self.assertEqual('EOF', s)
        self.assertEqual(True, quoted)

    def testDisambiguatePrefix(self):
        w = _assertReadWord(self, '${#}')
        self.assertEqual('#', _GetVarSub(self, w).token.tval)
        w = _assertReadWord(self, '${!}')
        self.assertEqual('!', _GetVarSub(self, w).token.tval)
        w = _assertReadWord(self, '${?}')
        self.assertEqual('?', _GetVarSub(self, w).token.tval)

        w = _assertReadWord(self, '${var}')

        w = _assertReadWord(self, '${15}')

        w = _assertReadWord(self, '${#var}')
        self.assertEqual(Id.VSub_Pound, _GetPrefixOp(self, w))
        w = _assertReadWord(self, '${!ref}')
        self.assertEqual(Id.VSub_Bang, _GetPrefixOp(self, w))

        # Length of length
        w = _assertReadWord(self, '${##}')
        self.assertEqual('#', _GetVarSub(self, w).token.tval)
        self.assertEqual(Id.VSub_Pound, _GetPrefixOp(self, w))

        w = _assertReadWord(self, '${array[0]}')
        self.assertEqual(1, len(w.parts))
        w = _assertReadWord(self, '${array[@]}')
        self.assertEqual(1, len(w.parts))

        # Length of element
        w = _assertReadWord(self, '${#array[0]}')
        self.assertEqual(1, len(w.parts))
        self.assertEqual(Id.VSub_Pound, _GetPrefixOp(self, w))
        # Ref for element
        w = _assertReadWord(self, '${!array[0]}')
        self.assertEqual(1, len(w.parts))
        self.assertEqual(Id.VSub_Bang, _GetPrefixOp(self, w))

        w = _assertReadWord(self, '${var#prefix}')
        self.assertEqual(1, len(w.parts))
        self.assertEqual(Id.VOp1_Pound, _GetSuffixOp(self, w).op.id)

        w = _assertReadWord(self, '${!var#prefix}')
        self.assertEqual(1, len(w.parts))
        self.assertEqual(Id.VSub_Bang, _GetPrefixOp(self, w))
        self.assertEqual(Id.VOp1_Pound, _GetSuffixOp(self, w).op.id)

        _assertReadWordFailure(self, '${#var#prefix}')

        # Allowed by bash, but we don't parse it.  Use len=$#; echo ${len#2}
        # instead.
        _assertReadWordFailure(self, '${##2}')

    def testIncompleteWords(self):
        # Bugs found in completion
        w = _assertReadWordFailure(self, '${undef:-')
        w = _assertReadWordFailure(self, '${undef:-$')
        w = _assertReadWordFailure(self, '${undef:-$F')

        w = _assertReadWordFailure(self, '${x@')
        w = _assertReadWordFailure(self, '${x@Q')

        w = _assertReadWordFailure(self, '${x%')

        w = _assertReadWordFailure(self, '${x/')
        w = _assertReadWordFailure(self, '${x/a/')
        w = _assertReadWordFailure(self, '${x/a/b')
        w = _assertReadWordFailure(self, '${x:')

    def testVarOf(self):
        w = _assertReadWord(self, '${name}')
        w = _assertReadWord(self, '${name[0]}')

        w = _assertReadWord(self, '${array[@]}')

        # Should be DISALLOWED!
        #w = _assertReadWord(self, '${11[@]}')

    def assertUnquoted(self, expected, w):
        ok, s, quoted = word_.StaticEval(w)
        self.assertTrue(ok)
        self.assertEqual(expected, s)
        self.assertFalse(quoted)

    def testPatSub(self):
        w = _assertReadWord(self, '${var/pat/replace}')
        op = _GetSuffixOp(self, w)
        self.assertUnquoted('pat', op.pat)
        self.assertUnquoted('replace', op.replace)
        self.assertEqual(Id.Undefined_Tok, op.replace_mode)

        w = _assertReadWord(self, '${var//pat/replace}')  # sub all
        op = _GetSuffixOp(self, w)
        self.assertUnquoted('pat', op.pat)
        self.assertUnquoted('replace', op.replace)
        self.assertEqual(Id.Lit_Slash, op.replace_mode,
                         Id_str(op.replace_mode))

        w = _assertReadWord(self, '${var/%pat/replace}')  # prefix
        op = _GetSuffixOp(self, w)
        self.assertUnquoted('pat', op.pat)
        self.assertUnquoted('replace', op.replace)
        self.assertEqual(Id.Lit_Percent, op.replace_mode)

        w = _assertReadWord(self, '${var/#pat/replace}')  # suffix
        op = _GetSuffixOp(self, w)
        self.assertUnquoted('pat', op.pat)
        self.assertUnquoted('replace', op.replace)
        self.assertEqual(Id.Lit_Pound, op.replace_mode)

        w = _assertReadWord(self, '${var/pat}')  # no replacement
        w = _assertReadWord(self, '${var//pat}')  # no replacement
        op = _GetSuffixOp(self, w)
        self.assertUnquoted('pat', op.pat)
        self.assertEqual(rhs_word_e.Empty, op.replace.tag())
        self.assertEqual(Id.Lit_Slash, op.replace_mode)

        # replace with slash
        w = _assertReadWord(self, '${var/pat//}')
        op = _GetSuffixOp(self, w)
        self.assertUnquoted('pat', op.pat)
        self.assertUnquoted('/', op.replace)

        # replace with two slashes unquoted
        w = _assertReadWord(self, '${var/pat///}')
        op = _GetSuffixOp(self, w)
        self.assertUnquoted('pat', op.pat)
        self.assertUnquoted('//', op.replace)

        # replace with two slashes quoted
        w = _assertReadWord(self, '${var/pat/"//"}')
        op = _GetSuffixOp(self, w)
        self.assertUnquoted('pat', op.pat)

        ok, s, quoted = word_.StaticEval(op.replace)
        self.assertTrue(ok)
        self.assertEqual('//', s)
        self.assertTrue(quoted)

        # Real example found in the wild!
        # http://www.oilshell.org/blog/2016/11/07.html

        # 2023-05: copied into spec/var-op-patsub.test.sh
        w = _assertReadWord(self, r'${var////\\/}')
        op = _GetSuffixOp(self, w)
        self.assertEqual(Id.Lit_Slash, op.replace_mode)

        self.assertUnquoted('/', op.pat)

        ok, s, quoted = word_.StaticEval(op.replace)
        self.assertTrue(ok)
        self.assertEqual(r'\/', s)

    def testSlice(self):
        w = _assertReadWord(self, '${foo:0}')
        # No length
        self.assertEqual(None, _GetSuffixOp(self, w).length)

        w = _assertReadWord(self, '${foo:0:1}')
        w = _assertReadWord(self, '${foo:1+2:2+3}')

        # This is allowed
        w = _assertReadWord(self, '${foo::1}')
        # No beginning
        self.assertEqual(None, _GetSuffixOp(self, w).begin)

    def testLength(self):
        # Synonym for $#, had a bug here
        w = _assertReadWord(self, '${#@}')
        self.assertTrue(Id.VSub_Pound, _GetPrefixOp(self, w))

        # Length of arg 11
        w = _assertReadWord(self, '${#11}')
        self.assertTrue(Id.VSub_Pound, _GetPrefixOp(self, w))

        w = _assertReadWord(self, '${#str}')
        self.assertTrue(Id.VSub_Pound, _GetPrefixOp(self, w))

        w = _assertReadWord(self, '${#array[0]}')
        # BUG!
        #self.assertTrue(VS_POUND, _GetSuffixOp(self, w).id)

        w = _assertReadWord(self, '${#array["key"]}')
        # BUG!
        #self.assertTrue(Id.VSub_POUND, _GetSuffixOp(self, w).id)

    def testUnary(self):
        w = _assertReadWord(self, '${var#}')
        self.assertTrue(Id.VOp1_Pound, _GetSuffixOp(self, w).op.id)
        w = _assertReadWord(self, '${var#prefix}')
        self.assertTrue(Id.VOp1_Pound, _GetSuffixOp(self, w).op.id)

        w = _assertReadWord(self, '${var##}')
        self.assertTrue(Id.VOp1_DPound, _GetSuffixOp(self, w).op.id)
        w = _assertReadWord(self, '${var##prefix}')
        self.assertTrue(Id.VOp1_DPound, _GetSuffixOp(self, w).op.id)

        w = _assertReadWord(self, '${var%suffix}')
        w = _assertReadWord(self, '${var%%suffix}')

    def testArrayOp(self):
        w = _assertReadWord(self, '${array[0]}')
        w = _assertReadWord(self, '${array[5+5]}')

        w = _assertReadWord(self, '${array[@]}')
        w = _assertReadWord(self, '${array[*]}')

    def testTestOp(self):
        w = _assertReadWord(self, '${var:-default]}')

    def testTildeLike(self):
        w = _assertReadWord(self, '~/git/oilshell/oil')
        w = _assertReadWord(self, '~andy/git/oilshell/oil')
        w = _assertReadWord(self, '~andy_c/git/oilshell/oil')
        w = _assertReadWord(self, '~andy.c/git/oilshell/oil')
        w = _assertReadWord(self, '~andy-c/git/oilshell/oil')
        w = _assertReadWord(self, '~andy-c:git/oilshell/oil')

    def testRead(self):
        CASES = [
            'ls "foo"',
            '$(( 1 + 2 ))',
            '$(echo $(( 1 )) )',  # OLD BUG: arith sub within command sub
            'echo ${#array[@]} b',  # Had a bug here
            'echo $(( ${#array[@]} ))',  # Bug here

            # Had a bug: unary minus
            #'${mounted_disk_regex:0:-1}',
            'echo ${@%suffix}',  # had a bug here
            '${@}',
            'echo ${var,,}',
            'echo ${var,,?}',

            # Line continuation tests
            '${\\\nfoo}',  # VSub_1
            '${foo\\\n}',  # VSub_2
            '${foo#\\\nyo}',  # VS_ARG_UNQ
            '"${foo#\\\nyo}"',  # VS_ARG_DQ
        ]
        for expr in CASES:
            print('---')
            print(expr)
            print()

            w_parser = test_lib.InitWordParser(expr)

            while True:
                w = w_parser.ReadWord(lex_mode_e.ShCommand)
                assert w is not None

                fmt.PrettyPrint(w)

                if word_.CommandId(w) == Id.Eof_Real:
                    break

    def testOilSplice(self):
        w = _assertReadWord(self, '@words', oil_at=True)

        # These are normal words
        w = _assertReadWord(self, '.@words', oil_at=True)
        w = _assertReadWord(self, '.@words.', oil_at=True)

        # Errors
        _assertReadWordFailure(self, '@words[', oil_at=True)
        _assertReadWordFailure(self, '@words.', oil_at=True)

    def testReadComment(self):
        # Test that we get Id.Op_Newline
        code = 'foo # comment\nbar #comment\n'
        w_parser = test_lib.InitWordParser(code)
        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        assert w
        self.assertEqual('foo', w.parts[0].tval)

        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        assert w
        self.assertEqual(Id.Op_Newline, w.id)

        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        assert w
        self.assertEqual('bar', w.parts[0].tval)

        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        assert w
        self.assertEqual(Id.Op_Newline, w.id)

        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        assert w
        self.assertEqual(Id.Eof_Real, w.id)

    def testReadRegex(self):
        # Test that we get Id.Op_Newline
        code = '(foo|bar)'
        w_parser = test_lib.InitWordParser(code)
        w_parser.next_lex_mode = lex_mode_e.BashRegex  # needed at beginning

        w = w_parser.ReadWord(lex_mode_e.BashRegex)
        assert w
        self.assertEqual('(', w.parts[0].tval)
        self.assertEqual('foo', w.parts[1].tval)
        self.assertEqual('|', w.parts[2].tval)
        self.assertEqual('bar', w.parts[3].tval)
        self.assertEqual(')', w.parts[4].tval)
        self.assertEqual(5, len(w.parts))

        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        assert w
        self.assertEqual(Id.Eof_Real, w.id)

    def testReadArithWord(self):
        w = _assertReadWord(self, '$(( (1+2) ))')
        child = w.parts[0].anode
        self.assertEqual(arith_expr_e.Binary, child.tag())

        w = _assertReadWord(self, '$(( (1+2) ))')
        child = w.parts[0].anode
        self.assertEqual(arith_expr_e.Binary, child.tag())

    def testReadArith(self):
        CASES = [
            '1 + 2',
            'a + b',
            '$a * $b',
            '${a} * ${b}',
            '$(echo 1) * $(echo 2)',
            '`echo 1` + 2',
            '$((1 + 2)) * $((3 + 4))',
            "'single quoted'",  # Allowed by oil but not bash
            '"${a}" + "${b}"',  # Ditto
            '$# + $$',
            # This doesn't work but does in bash -- should be 15
            #'$(( $(echo 1)$(echo 2) + 3 ))',
            '$(( x[0] < 5 ))',
            '$(( ++i ))',
            '$(( i++ ))',
            '$(( x -= 1))',
            '$(( x |= 1))',
            '$(( x[0] = 1 ))',
            '$(( 1 | 0 ))',
            '$((0x$size))',
        ]

        for expr in CASES:
            print('---')
            print(expr)
            print()

            w_parser = test_lib.InitWordParser(expr)
            # Can we remove this initialization?
            w_parser._SetNext(lex_mode_e.Arith)

            while True:
                w = w_parser.ReadArithWord()
                assert w is not None
                fmt.PrettyPrint(w)
                if word_.CommandId(w) in (Id.Eof_Real, Id.Unknown_Tok):
                    break

    def testHereDoc(self):
        w_parser = test_lib.InitWordParser("""\
ls foo

# Multiple newlines and comments should be ignored

ls bar
""")

        def assertWord(w, id_, val):
            self.assertEqual(1, len(w.parts))
            part = w.parts[0]
            self.assertEqual(id_, part.id)
            self.assertEqual(val, part.tval)

        print('--MULTI')
        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        assertWord(w, Id.Lit_Chars, 'ls')

        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        assertWord(w, Id.Lit_Chars, 'foo')

        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        self.assertEqual(word_e.Operator, w.tag())
        self.assertEqual(Id.Op_Newline, w.id)
        self.assertEqual(None, w.tval)

        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        assertWord(w, Id.Lit_Chars, 'ls')

        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        assertWord(w, Id.Lit_Chars, 'bar')

        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        self.assertEqual(word_e.Operator, w.tag())
        self.assertEqual(Id.Op_Newline, w.id)
        self.assertEqual(None, w.tval)

        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        self.assertEqual(word_e.Operator, w.tag())
        self.assertEqual(Id.Eof_Real, w.id)
        self.assertEqual('', w.tval)

    def testUnicode(self):
        words = 'z \xce\xbb \xe4\xb8\x89 \xf0\x9f\x98\x98'

        w_parser = test_lib.InitWordParser(words)
        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        self.assertEqual('z', w.parts[0].tval)

        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        self.assertEqual('\xce\xbb', w.parts[0].tval)

        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        self.assertEqual('\xe4\xb8\x89', w.parts[0].tval)

        w = w_parser.ReadWord(lex_mode_e.ShCommand)
        self.assertEqual('\xf0\x9f\x98\x98', w.parts[0].tval)

    def testParseErrorLocation(self):
        w = _assertSpanForWord(self, 'a=(1 2 3)')

        w = _assertSpanForWord(self, 'foo')

        w = _assertSpanForWord(self, '\\$')

        w = _assertSpanForWord(self, "''")

        w = _assertSpanForWord(self, "'sq'")

        w = _assertSpanForWord(self, '""')

        w = _assertSpanForWord(self, '"dq"')

        w = _assertSpanForWord(self, '$(echo command sub)')

        w = _assertSpanForWord(self, '$(( 1 + 2 ))')

        w = _assertSpanForWord(self, '~user')

        w = _assertSpanForWord(self, '${var#}')


if __name__ == '__main__':
    unittest.main()
