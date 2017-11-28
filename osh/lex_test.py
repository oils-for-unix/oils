#!/usr/bin/env python
"""
lex_test.py: Tests for lex.py
"""

import unittest

from core import alloc
from core.id_kind import Id, Kind, LookupKind
from core.lexer import CompileAll, Lexer, LineLexer
from core import test_lib
from core.test_lib import TokensEqual

from osh import parse_lib
from osh import ast_ as ast
from osh.lex import LEXER_DEF

lex_mode_e = ast.lex_mode_e


def _InitLexer(s):
  arena = test_lib.MakeArena('<lex_test.py>')
  _, lexer = parse_lib.InitLexer(s, arena=arena)
  return lexer


class AsdlTest(unittest.TestCase):

  def testLexMode(self):
    print lex_mode_e.DQ



CMD = """\
ls /
ls /home/
"""

class LexerTest(unittest.TestCase):

  def assertTokensEqual(self, left, right):
    self.assertTrue(
        TokensEqual(left, right), 'Expected %r, got %r' % (left, right))

  def testRead(self):
    lexer = _InitLexer(CMD)

    t = lexer.Read(lex_mode_e.OUTER)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'ls'), t)
    t = lexer.Read(lex_mode_e.OUTER)

    self.assertTokensEqual(ast.token(Id.WS_Space, ' '), t)

    t = lexer.Read(lex_mode_e.OUTER)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, '/'), t)

    t = lexer.Read(lex_mode_e.OUTER)
    self.assertTokensEqual(ast.token(Id.Op_Newline, '\n'), t)

    # Line two
    t = lexer.Read(lex_mode_e.OUTER)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'ls'), t)

    t = lexer.Read(lex_mode_e.OUTER)
    self.assertTokensEqual(ast.token(Id.WS_Space, ' '), t)

    t = lexer.Read(lex_mode_e.OUTER)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, '/home/'), t)

    t = lexer.Read(lex_mode_e.OUTER)
    self.assertTokensEqual(ast.token(Id.Op_Newline, '\n'), t)

    t = lexer.Read(lex_mode_e.OUTER)
    self.assertTokensEqual(ast.token(Id.Eof_Real, ''), t)

    # Another EOF gives EOF
    t = lexer.Read(lex_mode_e.OUTER)
    self.assertTokensEqual(ast.token(Id.Eof_Real, ''), t)

  def testRead_VS_ARG_UNQ(self):
    # Another EOF gives EOF
    lexer = _InitLexer("'hi'")
    t = lexer.Read(lex_mode_e.VS_ARG_UNQ)
    #self.assertTokensEqual(ast.token(Id.Eof_Real, ''), t)
    #t = l.Read(lex_mode_e.VS_ARG_UNQ)
    print(t)

  def testExtGlob(self):
    lexer = _InitLexer('@(foo|bar)')

    t = lexer.Read(lex_mode_e.OUTER)
    self.assertTokensEqual(ast.token(Id.ExtGlob_At, '@('), t)

    t = lexer.Read(lex_mode_e.EXTGLOB)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'foo'), t)

    t = lexer.Read(lex_mode_e.EXTGLOB)
    self.assertTokensEqual(ast.token(Id.Op_Pipe, '|'), t)

    t = lexer.Read(lex_mode_e.EXTGLOB)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'bar'), t)

    t = lexer.Read(lex_mode_e.EXTGLOB)
    self.assertTokensEqual(ast.token(Id.Op_RParen, ')'), t)

    # Individual cases

    lexer = _InitLexer('@(')
    t = lexer.Read(lex_mode_e.EXTGLOB)
    self.assertTokensEqual(ast.token(Id.ExtGlob_At, '@('), t)

    lexer = _InitLexer('*(')
    t = lexer.Read(lex_mode_e.EXTGLOB)
    self.assertTokensEqual(ast.token(Id.ExtGlob_Star, '*('), t)

    lexer = _InitLexer('?(')
    t = lexer.Read(lex_mode_e.EXTGLOB)
    self.assertTokensEqual(ast.token(Id.ExtGlob_QMark, '?('), t)

    lexer = _InitLexer('$')
    t = lexer.Read(lex_mode_e.EXTGLOB)
    self.assertTokensEqual(ast.token(Id.Lit_Other, '$'), t)

  def testBashRegexState(self):
    lexer = _InitLexer('(foo|bar)')

    t = lexer.Read(lex_mode_e.BASH_REGEX)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, '('), t)

    t = lexer.Read(lex_mode_e.BASH_REGEX)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'foo'), t)

    t = lexer.Read(lex_mode_e.BASH_REGEX)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, '|'), t)

  def testDBracketState(self):
    lexer = _InitLexer('-z foo')
    t = lexer.Read(lex_mode_e.DBRACKET)
    self.assertTokensEqual(ast.token(Id.BoolUnary_z, '-z'), t)
    self.assertEqual(Kind.BoolUnary, LookupKind(t.id))

  def testLookAhead(self):
    # I think this is the usage pattern we care about.  Peek and Next() past
    # the function; then Peek() the next token.  Then Lookahead in that state.
    lexer = _InitLexer('func()')

    t = lexer.Read(lex_mode_e.OUTER)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'func'), t)

    #self.assertEqual(Id.Op_LParen, lexer.LookAhead())

    t = lexer.Read(lex_mode_e.OUTER)
    self.assertTokensEqual(ast.token(Id.Op_LParen, '('), t)

    self.assertTokensEqual(
        ast.token(Id.Op_RParen, ')'), lexer.LookAhead(lex_mode_e.OUTER))

    lexer = _InitLexer('func ()')

    t = lexer.Read(lex_mode_e.OUTER)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'func'), t)

    t = lexer.Read(lex_mode_e.OUTER)
    self.assertTokensEqual(ast.token(Id.WS_Space, ' '), t)

    self.assertTokensEqual(
        ast.token(Id.Op_LParen, '('), lexer.LookAhead(lex_mode_e.OUTER))


class LineLexerTest(unittest.TestCase):

  def assertTokensEqual(self, left, right):
    self.assertTrue(TokensEqual(left, right))

  def testReadOuter(self):
    # Lines always end with '\n'
    l = LineLexer(parse_lib._MakeMatcher(), '')
    try:
      l.Read(lex_mode_e.OUTER)
    except AssertionError as e:
      print(e)
    else:
      raise AssertionError('Expected error')

    l = LineLexer(parse_lib._MakeMatcher(), '\n')
    self.assertTokensEqual(
        ast.token(Id.Op_Newline, '\n'), l.Read(lex_mode_e.OUTER))

  def testRead_VS_ARG_UNQ(self):
    l = LineLexer(parse_lib._MakeMatcher(), "'hi'")
    t = l.Read(lex_mode_e.VS_ARG_UNQ)
    self.assertEqual(Id.Left_SingleQuote, t.id)

  def testLookAhead(self):
    # Lines always end with '\n'
    l = LineLexer(parse_lib._MakeMatcher(), '')
    self.assertTokensEqual(
        ast.token(Id.Unknown_Tok, ''), l.LookAhead(lex_mode_e.OUTER))

    l = LineLexer(parse_lib._MakeMatcher(), 'foo')
    self.assertTokensEqual(
        ast.token(Id.Lit_Chars, 'foo'), l.Read(lex_mode_e.OUTER))
    self.assertTokensEqual(
        ast.token(Id.Unknown_Tok, ''), l.LookAhead(lex_mode_e.OUTER))

    l = LineLexer(parse_lib._MakeMatcher(), 'foo  bar')
    self.assertTokensEqual(
        ast.token(Id.Lit_Chars, 'foo'), l.Read(lex_mode_e.OUTER))
    self.assertTokensEqual(
        ast.token(Id.Lit_Chars, 'bar'), l.LookAhead(lex_mode_e.OUTER))

    # No lookahead; using the cursor!
    l = LineLexer(parse_lib._MakeMatcher(), 'func(')
    self.assertTokensEqual(
        ast.token(Id.Lit_Chars, 'func'), l.Read(lex_mode_e.OUTER))
    self.assertTokensEqual(
        ast.token(Id.Op_LParen, '('), l.LookAhead(lex_mode_e.OUTER))

    l = LineLexer(parse_lib._MakeMatcher(), 'func  (')
    self.assertTokensEqual(
        ast.token(Id.Lit_Chars, 'func'), l.Read(lex_mode_e.OUTER))
    self.assertTokensEqual(
        ast.token(Id.Op_LParen, '('), l.LookAhead(lex_mode_e.OUTER))


OUTER_RE = CompileAll(LEXER_DEF[lex_mode_e.OUTER])
DOUBLE_QUOTED_RE = CompileAll(LEXER_DEF[lex_mode_e.DQ])


class RegexTest(unittest.TestCase):

  def testOuter(self):
    o = OUTER_RE
    nul_pat, _ = o[3]
    print(nul_pat.match('\0'))

  def testDoubleQuoted(self):
    d = DOUBLE_QUOTED_RE
    nul_pat, _ = d[3]
    print(nul_pat.match('\0'))


if __name__ == '__main__':
  unittest.main()
