#!/usr/bin/env python
"""
lex_test.py: Tests for lex.py
"""
from __future__ import print_function

import re
import unittest

from _devbuild.gen.id_kind_asdl import Id, Kind
from frontend import lex
from frontend import match
from frontend.lexer import LineLexer

from core import test_lib
from core.meta import syntax_asdl, LookupKind, types_asdl

lex_mode_e = types_asdl.lex_mode_e
token = syntax_asdl.token


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
    self.assertTrue(
        test_lib.TokensEqual(left, right),
        'Expected %r, got %r' % (left, right))

  def testRead(self):
    lexer = _InitLexer(CMD)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(syntax_asdl.token(Id.Lit_Chars, 'ls'), t)
    t = lexer.Read(lex_mode_e.Outer)

    self.assertTokensEqual(syntax_asdl.token(Id.WS_Space, ' '), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(syntax_asdl.token(Id.Lit_Chars, '/'), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(syntax_asdl.token(Id.Op_Newline, '\n'), t)

    # Line two
    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(syntax_asdl.token(Id.Lit_Chars, 'ls'), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(syntax_asdl.token(Id.WS_Space, ' '), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(syntax_asdl.token(Id.Lit_Chars, '/home/'), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(syntax_asdl.token(Id.Op_Newline, '\n'), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(syntax_asdl.token(Id.Eof_Real, ''), t)

    # Another EOF gives EOF
    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(syntax_asdl.token(Id.Eof_Real, ''), t)

  def testMode_VS_ArgUnquoted(self):
    # Another EOF gives EOF
    lexer = _InitLexer("'hi'")
    t = lexer.Read(lex_mode_e.VS_ArgUnquoted)
    #self.assertTokensEqual(syntax_asdl.token(Id.Eof_Real, ''), t)
    #t = l.Read(lex_mode_e.VS_ArgUnquoted)
    print(t)

  def testMode_ExtGlob(self):
    lexer = _InitLexer('@(foo|bar)')

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(syntax_asdl.token(Id.ExtGlob_At, '@('), t)

    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(syntax_asdl.token(Id.Lit_Chars, 'foo'), t)

    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(syntax_asdl.token(Id.Op_Pipe, '|'), t)

    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(syntax_asdl.token(Id.Lit_Chars, 'bar'), t)

    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(syntax_asdl.token(Id.Op_RParen, ')'), t)

    # Individual cases

    lexer = _InitLexer('@(')
    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(syntax_asdl.token(Id.ExtGlob_At, '@('), t)

    lexer = _InitLexer('*(')
    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(syntax_asdl.token(Id.ExtGlob_Star, '*('), t)

    lexer = _InitLexer('?(')
    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(syntax_asdl.token(Id.ExtGlob_QMark, '?('), t)

    lexer = _InitLexer('$')
    t = lexer.Read(lex_mode_e.ExtGlob)
    self.assertTokensEqual(syntax_asdl.token(Id.Lit_Other, '$'), t)

  def testMode_BashRegex(self):
    lexer = _InitLexer('(foo|bar)')

    t = lexer.Read(lex_mode_e.BashRegex)
    self.assertTokensEqual(syntax_asdl.token(Id.Lit_Other, '('), t)

    t = lexer.Read(lex_mode_e.BashRegex)
    self.assertTokensEqual(syntax_asdl.token(Id.Lit_Chars, 'foo'), t)

    t = lexer.Read(lex_mode_e.BashRegex)
    self.assertTokensEqual(syntax_asdl.token(Id.Lit_Other, '|'), t)

  def testMode_DBracket(self):
    lexer = _InitLexer('-z foo')
    t = lexer.Read(lex_mode_e.DBracket)
    self.assertTokensEqual(syntax_asdl.token(Id.BoolUnary_z, '-z'), t)
    self.assertEqual(Kind.BoolUnary, LookupKind(t.id))

  def testMode_DollarSq(self):
    lexer = _InitLexer(r'foo bar\n \x00 \000 \u0065')

    t = lexer.Read(lex_mode_e.DollarSQ)
    print(t)
    self.assertTokensEqual(syntax_asdl.token(Id.Char_Literals, 'foo bar'), t)

    t = lexer.Read(lex_mode_e.DollarSQ)
    print(t)
    self.assertTokensEqual(syntax_asdl.token(Id.Char_OneChar, r'\n'), t)

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

  def testLookAhead(self):
    # I think this is the usage pattern we care about.  Peek and Next() past
    # the function; then Peek() the next token.  Then Lookahead in that state.
    lexer = _InitLexer('func()')

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(syntax_asdl.token(Id.Lit_Chars, 'func'), t)

    #self.assertEqual(Id.Op_LParen, lexer.LookAhead())

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(syntax_asdl.token(Id.Op_LParen, '('), t)

    self.assertTokensEqual(
        syntax_asdl.token(Id.Op_RParen, ')'), lexer.LookAhead(lex_mode_e.Outer))

    lexer = _InitLexer('func ()')

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(syntax_asdl.token(Id.Lit_Chars, 'func'), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(syntax_asdl.token(Id.WS_Space, ' '), t)

    self.assertTokensEqual(
        syntax_asdl.token(Id.Op_LParen, '('), lexer.LookAhead(lex_mode_e.Outer))

  def testPushHint(self):
    # Extglob use case
    lexer = _InitLexer('@()')
    lexer.PushHint(Id.Op_RParen, Id.Right_ExtGlob)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(token(Id.ExtGlob_At, '@('), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(token(Id.Right_ExtGlob, ')'), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(token(Id.Eof_Real, ''), t)

  def testEmitCompDummy(self):
    lexer = _InitLexer('echo ')
    lexer.EmitCompDummy()

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(token(Id.Lit_Chars, 'echo'), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(token(Id.WS_Space, ' '), t)

    # Right before EOF
    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(token(Id.Lit_CompDummy, ''), t)

    t = lexer.Read(lex_mode_e.Outer)
    self.assertTokensEqual(token(Id.Eof_Real, ''), t)


class LineLexerTest(unittest.TestCase):

  def setUp(self):
    self.arena = test_lib.MakeArena('<lex_test.py>')

  def assertTokensEqual(self, left, right):
    self.assertTrue(test_lib.TokensEqual(left, right))

  def testReadOuter(self):
    l = LineLexer(match.MATCHER, '\n', self.arena)
    self.assertTokensEqual(
        syntax_asdl.token(Id.Op_Newline, '\n'), l.Read(lex_mode_e.Outer))

  def testRead_VS_ARG_UNQ(self):
    l = LineLexer(match.MATCHER, "'hi'", self.arena)
    t = l.Read(lex_mode_e.VS_ArgUnquoted)
    self.assertEqual(Id.Left_SingleQuote, t.id)

  def testLookAhead(self):
    # Lines always end with '\n'
    l = LineLexer(match.MATCHER, '', self.arena)
    self.assertTokensEqual(
        syntax_asdl.token(Id.Unknown_Tok, ''), l.LookAhead(lex_mode_e.Outer))

    l = LineLexer(match.MATCHER, 'foo', self.arena)
    self.assertTokensEqual(
        syntax_asdl.token(Id.Lit_Chars, 'foo'), l.Read(lex_mode_e.Outer))
    self.assertTokensEqual(
        syntax_asdl.token(Id.Unknown_Tok, ''), l.LookAhead(lex_mode_e.Outer))

    l = LineLexer(match.MATCHER, 'foo  bar', self.arena)
    self.assertTokensEqual(
        syntax_asdl.token(Id.Lit_Chars, 'foo'), l.Read(lex_mode_e.Outer))
    self.assertTokensEqual(
        syntax_asdl.token(Id.Lit_Chars, 'bar'), l.LookAhead(lex_mode_e.Outer))

    # No lookahead; using the cursor!
    l = LineLexer(match.MATCHER, 'func(', self.arena)
    self.assertTokensEqual(
        syntax_asdl.token(Id.Lit_Chars, 'func'), l.Read(lex_mode_e.Outer))
    self.assertTokensEqual(
        syntax_asdl.token(Id.Op_LParen, '('), l.LookAhead(lex_mode_e.Outer))

    l = LineLexer(match.MATCHER, 'func  (', self.arena)
    self.assertTokensEqual(
        syntax_asdl.token(Id.Lit_Chars, 'func'), l.Read(lex_mode_e.Outer))
    self.assertTokensEqual(
        syntax_asdl.token(Id.Op_LParen, '('), l.LookAhead(lex_mode_e.Outer))


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

  def testHistoryLexer(self):
    lex = match.HISTORY_LEXER

    print(list(lex.Tokens(r'echo hi')))

    print(list(lex.Tokens(r'echo !! !* !^ !$')))

    # No history operator with \ escape
    tokens = list(lex.Tokens(r'echo \!!'))
    print(tokens)
    self.assert_(Id.History_Op not in [tok_type for tok_type, _ in tokens])

    print(list(lex.Tokens(r'echo !3...')))
    print(list(lex.Tokens(r'echo !-5...')))
    print(list(lex.Tokens(r'echo !x/foo.py bar')))

    print('---')

    # No history operator in single quotes
    tokens = list(lex.Tokens(r"echo '!!' $'!!' "))
    print(tokens)
    self.assert_(Id.History_Op not in [tok_type for tok_type, _ in tokens])

    # No history operator in incomplete single quotes
    tokens = list(lex.Tokens(r"echo '!! "))
    print(tokens)
    self.assert_(Id.History_Op not in [tok_type for tok_type, _ in tokens])

    # Quoted single quote, and then a History operator
    tokens = list(lex.Tokens(r"echo \' !! "))
    print(tokens)
    # YES operator
    self.assert_(Id.History_Op in [tok_type for tok_type, _ in tokens])


if __name__ == '__main__':
  unittest.main()
