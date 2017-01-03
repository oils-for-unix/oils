#!/usr/bin/python3
"""
lex_test.py: Tests for lex.py
"""

import unittest

from core.id_kind import Id, Kind, LookupKind
from core.lexer import CompileAll, Lexer, LineLexer, FindLongestMatch
from core.tokens import TokensEqual

from osh import parse_lib
from osh import ast_ as ast
from osh.lex import LEXER_DEF, LexMode


def _InitLexer(s):
  _, lexer = parse_lib.InitLexer(s)
  return lexer


CMD = """\
ls /
ls /home/
"""

class LexerTest(unittest.TestCase):

  def assertTokensEqual(self, left, right):
    self.assertTrue(TokensEqual(left, right))

  def testRead(self):
    lexer = _InitLexer(CMD)

    t = lexer.Read(LexMode.OUTER)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'ls'), t)
    t = lexer.Read(LexMode.OUTER)

    self.assertTokensEqual(ast.token(Id.WS_Space, ' '), t)

    t = lexer.Read(LexMode.OUTER)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, '/'), t)

    t = lexer.Read(LexMode.OUTER)
    self.assertTokensEqual(ast.token(Id.Op_Newline, '\n'), t)

    # Line two
    t = lexer.Read(LexMode.OUTER)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'ls'), t)

    t = lexer.Read(LexMode.OUTER)
    self.assertTokensEqual(ast.token(Id.WS_Space, ' '), t)

    t = lexer.Read(LexMode.OUTER)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, '/home/'), t)

    t = lexer.Read(LexMode.OUTER)
    self.assertTokensEqual(ast.token(Id.Op_Newline, '\n'), t)

    t = lexer.Read(LexMode.OUTER)
    self.assertTokensEqual(ast.token(Id.Eof_Real, ''), t)

    # Another EOF gives EOF
    t = lexer.Read(LexMode.OUTER)
    self.assertTokensEqual(ast.token(Id.Eof_Real, ''), t)

  def testBashRegexState(self):
    lexer = _InitLexer('(foo|bar)')

    t = lexer.Read(LexMode.BASH_REGEX)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, '('), t)

    t = lexer.Read(LexMode.BASH_REGEX)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'foo'), t)

    t = lexer.Read(LexMode.BASH_REGEX)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, '|'), t)

  def testDBracketState(self):
    lexer = _InitLexer('-z foo')
    t = lexer.Read(LexMode.DBRACKET)
    self.assertTokensEqual(ast.token(Id.BoolUnary_z, '-z'), t)
    self.assertEqual(Kind.BoolUnary, LookupKind(t.id))

  def testLookAhead(self):
    # I think this is the usage pattern we care about.  Peek and Next() past
    # the function; then Peek() the next token.  Then Lookahead in that state.
    lexer = _InitLexer('func()')

    t = lexer.Read(LexMode.OUTER)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'func'), t)

    #self.assertEqual(Id.Op_LParen, lexer.LookAhead())

    t = lexer.Read(LexMode.OUTER)
    self.assertTokensEqual(ast.token(Id.Op_LParen, '('), t)

    self.assertTokensEqual(
        ast.token(Id.Op_RParen, ')'), lexer.LookAhead(LexMode.OUTER))

    lexer = _InitLexer('func ()')

    t = lexer.Read(LexMode.OUTER)
    self.assertTokensEqual(ast.token(Id.Lit_Chars, 'func'), t)

    t = lexer.Read(LexMode.OUTER)
    self.assertTokensEqual(ast.token(Id.WS_Space, ' '), t)

    self.assertTokensEqual(
        ast.token(Id.Op_LParen, '('), lexer.LookAhead(LexMode.OUTER))


class LineLexerTest(unittest.TestCase):

  def assertTokensEqual(self, left, right):
    self.assertTrue(TokensEqual(left, right))

  def testReadOuter(self):
    # Lines always end with '\n'
    l = LineLexer(LEXER_DEF, '')
    try:
      l.Read(LexMode.OUTER)
    except AssertionError as e:
      print(e)
    else:
      raise AssertionError('Expected error')

    l = LineLexer(LEXER_DEF, '\n')
    self.assertTokensEqual(
        ast.token(Id.Op_Newline, '\n'), l.Read(LexMode.OUTER))

  def testLookAhead(self):
    # Lines always end with '\n'
    l = LineLexer(LEXER_DEF, '')
    self.assertTokensEqual(
        ast.token(Id.Eof_Real, ''), l.LookAhead(LexMode.OUTER))

    l = LineLexer(LEXER_DEF, 'foo')
    self.assertTokensEqual(
        ast.token(Id.Lit_Chars, 'foo'), l.Read(LexMode.OUTER))
    self.assertTokensEqual(
        ast.token(Id.Eof_Real, ''), l.LookAhead(LexMode.OUTER))

    l = LineLexer(LEXER_DEF, 'foo  bar')
    self.assertTokensEqual(
        ast.token(Id.Lit_Chars, 'foo'), l.Read(LexMode.OUTER))
    self.assertEqual(
        ast.token(Id.Lit_Chars, 'bar'), l.LookAhead(LexMode.OUTER))

    # No lookahead; using the cursor!
    l = LineLexer(LEXER_DEF, 'func(')
    self.assertTokensEqual(
        ast.token(Id.Lit_Chars, 'func'), l.Read(LexMode.OUTER))
    self.assertTokensEqual(
        ast.token(Id.Op_LParen, '('), l.LookAhead(LexMode.OUTER))

    l = LineLexer(LEXER_DEF, 'func  (')
    self.assertTokensEqual(
        ast.token(Id.Lit_Chars, 'func'), l.Read(LexMode.OUTER))
    self.assertTokensEqual(
        ast.token(Id.Op_LParen, '('), l.LookAhead(LexMode.OUTER))


OUTER_RE = CompileAll(LEXER_DEF[LexMode.OUTER])
DOUBLE_QUOTED_RE = CompileAll(LEXER_DEF[LexMode.DQ])


class FunctionTest(unittest.TestCase):

  def testFindLongestMatch(self):
    e, tok_type, tok_val = FindLongestMatch(OUTER_RE, '  foo', 2)
    self.assertEqual(e, 5)
    self.assertEqual(tok_type, Id.Lit_Chars)
    self.assertEqual(tok_val, 'foo')

    e, tok_type, tok_val = FindLongestMatch(OUTER_RE, ' "foo"', 1)
    self.assertEqual(e, 2)
    self.assertEqual(tok_type, Id.Left_DoubleQuote)
    self.assertEqual(tok_val, '"')


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
