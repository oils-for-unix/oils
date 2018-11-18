#!/usr/bin/env python
"""
lex_test.py: Tests for lex.py
"""
from __future__ import print_function

import re
import unittest

from core.lexer import LineLexer
from core import test_lib

from frontend import lex
from frontend import match
from osh import parse_lib
from core.meta import ast, Id, Kind, LookupKind, types

lex_mode_e = types.lex_mode_e


def _InitLexer(s):
  arena = test_lib.MakeArena('<lex_test.py>')
  _, lexer = parse_lib.InitLexer(s, arena)
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
    self.assertTrue(
        test_lib.TokensEqual(left, right),
        'Expected %r, got %r' % (left, right))

  def testRead(self):
    lexer = _InitLexer(CMD)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'ls'), t)
    t = lexer.Read(lex_mode_e.Outer)

    self.assertTokensEqual(ast.token(Id.WS_Space, ' '), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, '/'), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(ast.token(Id.Op_Newline, '\n'), t)

    # Line two
    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'ls'), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(ast.token(Id.WS_Space, ' '), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, '/home/'), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(ast.token(Id.Op_Newline, '\n'), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(ast.token(Id.Eof_Real, ''), t)

    # Another EOF gives EOF
    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(ast.token(Id.Eof_Real, ''), t)

  def testRead_VS_ARG_UNQ(self):
    # Another EOF gives EOF
    lexer = _InitLexer("'hi'")
    t = lexer.Read(lex_mode_e.VS_ArgUnquoted)
    #self.assertTokensEqual(ast.token(Id.Eof_Real, ''), t)
    #t = l.Read(lex_mode_e.VS_ArgUnquoted)
    print(t)

  def testExtGlob(self):
    lexer = _InitLexer('@(foo|bar)')

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(ast.token(Id.ExtGlob_At, '@('), t)

    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'foo'), t)

    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(ast.token(Id.Op_Pipe, '|'), t)

    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'bar'), t)

    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(ast.token(Id.Op_RParen, ')'), t)

    # Individual cases

    lexer = _InitLexer('@(')
    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(ast.token(Id.ExtGlob_At, '@('), t)

    lexer = _InitLexer('*(')
    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(ast.token(Id.ExtGlob_Star, '*('), t)

    lexer = _InitLexer('?(')
    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(ast.token(Id.ExtGlob_QMark, '?('), t)

    lexer = _InitLexer('$')
    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(ast.token(Id.Lit_Other, '$'), t)

  def testBashRegexState(self):
    lexer = _InitLexer('(foo|bar)')

    t = lexer.Read(lex_mode_e.BashRegex)
    self.assertTokensEqual(ast.token(Id.Lit_Other, '('), t)

    t = lexer.Read(lex_mode_e.BashRegex)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'foo'), t)

    t = lexer.Read(lex_mode_e.BashRegex)
    self.assertTokensEqual(ast.token(Id.Lit_Other, '|'), t)

  def testDBracketState(self):
    lexer = _InitLexer('-z foo')
    t = lexer.Read(lex_mode_e.DBracket)
    self.assertTokensEqual(ast.token(Id.BoolUnary_z, '-z'), t)
    self.assertEqual(Kind.BoolUnary, LookupKind(t.id))

  def testDollarSqState(self):
    lexer = _InitLexer(r'foo bar\n \x00 \000 \u0065')

    t = lexer.Read(lex_mode_e.DollarSQ)
    print(t)
    self.assertTokensEqual(ast.token(Id.Char_Literals, 'foo bar'), t)

    t = lexer.Read(lex_mode_e.DollarSQ)
    print(t)
    self.assertTokensEqual(ast.token(Id.Char_OneChar, r'\n'), t)

  def testLookAhead(self):
    # I think this is the usage pattern we care about.  Peek and Next() past
    # the function; then Peek() the next token.  Then Lookahead in that state.
    lexer = _InitLexer('func()')

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'func'), t)

    #self.assertEqual(Id.Op_LParen, lexer.LookAhead())

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(ast.token(Id.Op_LParen, '('), t)

    self.assertTokensEqual(
        ast.token(Id.Op_RParen, ')'), lexer.LookAhead(lex_mode_e.Outer))

    lexer = _InitLexer('func ()')

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'func'), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(ast.token(Id.WS_Space, ' '), t)

    self.assertTokensEqual(
        ast.token(Id.Op_LParen, '('), lexer.LookAhead(lex_mode_e.Outer))


class LineLexerTest(unittest.TestCase):

  def setUp(self):
    self.arena = test_lib.MakeArena('<lex_test.py>')

  def assertTokensEqual(self, left, right):
    self.assertTrue(test_lib.TokensEqual(left, right))

  def testReadOuter(self):
    l = LineLexer(match.MATCHER, '\n', self.arena)
    self.assertTokensEqual(
        ast.token(Id.Op_Newline, '\n'), l.Read(lex_mode_e.Outer))

  def testRead_VS_ARG_UNQ(self):
    l = LineLexer(match.MATCHER, "'hi'", self.arena)
    t = l.Read(lex_mode_e.VS_ArgUnquoted)
    self.assertEqual(Id.Left_SingleQuote, t.id)

  def testLookAhead(self):
    # Lines always end with '\n'
    l = LineLexer(match.MATCHER, '', self.arena)
    self.assertTokensEqual(
        ast.token(Id.Unknown_Tok, ''), l.LookAhead(lex_mode_e.Outer))

    l = LineLexer(match.MATCHER, 'foo', self.arena)
    self.assertTokensEqual(
        ast.token(Id.Lit_Chars, 'foo'), l.Read(lex_mode_e.Outer))
    self.assertTokensEqual(
        ast.token(Id.Unknown_Tok, ''), l.LookAhead(lex_mode_e.Outer))

    l = LineLexer(match.MATCHER, 'foo  bar', self.arena)
    self.assertTokensEqual(
        ast.token(Id.Lit_Chars, 'foo'), l.Read(lex_mode_e.Outer))
    self.assertTokensEqual(
        ast.token(Id.Lit_Chars, 'bar'), l.LookAhead(lex_mode_e.Outer))

    # No lookahead; using the cursor!
    l = LineLexer(match.MATCHER, 'func(', self.arena)
    self.assertTokensEqual(
        ast.token(Id.Lit_Chars, 'func'), l.Read(lex_mode_e.Outer))
    self.assertTokensEqual(
        ast.token(Id.Op_LParen, '('), l.LookAhead(lex_mode_e.Outer))

    l = LineLexer(match.MATCHER, 'func  (', self.arena)
    self.assertTokensEqual(
        ast.token(Id.Lit_Chars, 'func'), l.Read(lex_mode_e.Outer))
    self.assertTokensEqual(
        ast.token(Id.Op_LParen, '('), l.LookAhead(lex_mode_e.Outer))


class RegexTest(unittest.TestCase):

  def testNul(self):
    nul_pat = re.compile(r'[\0]')
    self.assertEqual(False, bool(nul_pat.match('x')))
    self.assertEqual(True, bool(nul_pat.match('\0')))

    _, p, _ = lex.ECHO_E_DEF[-1]
    print('P %r' % p)
    last_echo_e_pat = re.compile(p)
    self.assertEqual(True, bool(last_echo_e_pat.match('x')))
    self.assertEqual(False, bool(last_echo_e_pat.match('\0')))


class OtherLexerTest(unittest.TestCase):

  def testEchoLexer(self):
    lex = match.ECHO_LEXER
    print(list(lex.Tokens(r'newline \n NUL \0 octal \0377 hex \x00')))
    print(list(lex.Tokens(r'unicode \u0065 \U00000065')))
    print(list(lex.Tokens(r'\d \e \f \g')))

    # NOTE: We only test with one of these.
    print(match.ECHO_MATCHER)  # either fast or slow

  def testPS1Lexer(self):
    lex = match.PS1_LEXER
    print(list(lex.Tokens(r'foo')))
    print(list(lex.Tokens(r'\h \w \$')))


if __name__ == '__main__':
  unittest.main()
