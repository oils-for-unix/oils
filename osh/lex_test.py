#!/usr/bin/python3
"""
lex_test.py: Tests for lex.py
"""

import unittest

from core.tokens import *
from core.lexer import CompileAll, Lexer, LineLexer, FindLongestMatch

from osh import parse_lib
#import sh_lexer  # module under test
from osh.lex import LEXER_DEF, LexMode


def _InitLexer(s):
  _, lexer = parse_lib.InitLexer(s)
  return lexer


CMD = """\
ls /
ls /home/
"""

class LexerTest(unittest.TestCase):

  def testRead(self):
    lexer = _InitLexer(CMD)

    t = lexer.Read(LexMode.OUTER)
    self.assertEqual(Token(LIT_CHARS, 'ls'), t)
    t = lexer.Read(LexMode.OUTER)
    self.assertEqual(Token(WS_SPACE, ' '), t)
    t = lexer.Read(LexMode.OUTER)
    self.assertEqual(Token(LIT_CHARS, '/'), t)
    t = lexer.Read(LexMode.OUTER)
    self.assertEqual(Token(OP_NEWLINE, '\n'), t)

    # Line two
    t = lexer.Read(LexMode.OUTER)
    self.assertEqual(Token(LIT_CHARS, 'ls'), t)
    t = lexer.Read(LexMode.OUTER)
    self.assertEqual(Token(WS_SPACE, ' '), t)
    t = lexer.Read(LexMode.OUTER)
    self.assertEqual(Token(LIT_CHARS, '/home/'), t)
    t = lexer.Read(LexMode.OUTER)
    self.assertEqual(Token(OP_NEWLINE, '\n'), t)
    t = lexer.Read(LexMode.OUTER)
    self.assertEqual(Token(Eof_REAL, ''), t)

    # Another EOF gives EOF
    t = lexer.Read(LexMode.OUTER)
    self.assertEqual(Token(Eof_REAL, ''), t)

  def testBashRegexState(self):
    lexer = _InitLexer('(foo|bar)')

    t = lexer.Read(LexMode.BASH_REGEX)
    self.assertEqual(Token(LIT_CHARS, '('), t)
    t = lexer.Read(LexMode.BASH_REGEX)
    self.assertEqual(Token(LIT_CHARS, 'foo'), t)
    t = lexer.Read(LexMode.BASH_REGEX)
    self.assertEqual(Token(LIT_CHARS, '|'), t)

  def testLookAheadForOp(self):
    # I think this is the usage pattern we care about.  Peek and Next() past
    # the function; then Peek() the next token.  Then Lookahead in that state.
    lexer = _InitLexer('func()')

    t = lexer.Read(LexMode.OUTER)
    self.assertEqual(Token(LIT_CHARS, 'func'), t)

    #self.assertEqual(OP_LPAREN, lexer.LookAheadForOp())

    t = lexer.Read(LexMode.OUTER)
    self.assertEqual(Token(OP_LPAREN, '('), t)

    self.assertEqual(
        Token(OP_RPAREN, ')'), lexer.LookAheadForOp(LexMode.OUTER))

    lexer = _InitLexer('func ()')

    t = lexer.Read(LexMode.OUTER)
    self.assertEqual(Token(LIT_CHARS, 'func'), t)

    t = lexer.Read(LexMode.OUTER)
    self.assertEqual(Token(WS_SPACE, ' '), t)

    self.assertEqual(
        Token(OP_LPAREN, '('), lexer.LookAheadForOp(LexMode.OUTER))


class LineLexerTest(unittest.TestCase):

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
    self.assertEqual(Token(OP_NEWLINE, '\n'), l.Read(LexMode.OUTER))

  def testLookAheadForOp(self):
    # Lines always end with '\n'
    l = LineLexer(LEXER_DEF, '')
    self.assertEqual(Token(Eof_REAL, ''), l.LookAheadForOp(LexMode.OUTER))

    l = LineLexer(LEXER_DEF, 'foo')
    self.assertEqual(Token(LIT_CHARS, 'foo'), l.Read(LexMode.OUTER))
    self.assertEqual(Token(Eof_REAL, ''), l.LookAheadForOp(LexMode.OUTER))

    l = LineLexer(LEXER_DEF, 'foo  bar')
    self.assertEqual(Token(LIT_CHARS, 'foo'), l.Read(LexMode.OUTER))
    self.assertEqual(Token(LIT_CHARS, 'bar'), l.LookAheadForOp(LexMode.OUTER))

    # No lookahead; using the cursor!
    l = LineLexer(LEXER_DEF, 'func(')
    self.assertEqual(Token(LIT_CHARS, 'func'), l.Read(LexMode.OUTER))
    self.assertEqual(Token(OP_LPAREN, '('), l.LookAheadForOp(LexMode.OUTER))

    l = LineLexer(LEXER_DEF, 'func  (')
    self.assertEqual(Token(LIT_CHARS, 'func'), l.Read(LexMode.OUTER))
    self.assertEqual(Token(OP_LPAREN, '('), l.LookAheadForOp(LexMode.OUTER))


OUTER_RE = CompileAll(LEXER_DEF[LexMode.OUTER])
DOUBLE_QUOTED_RE = CompileAll(LEXER_DEF[LexMode.DQ])


class FunctionTest(unittest.TestCase):

  def testFindLongestMatch(self):
    e, tok_type, tok_val = FindLongestMatch(OUTER_RE, '  foo', 2)
    self.assertEqual(e, 5)
    self.assertEqual(tok_type, LIT_CHARS)
    self.assertEqual(tok_val, 'foo')

    e, tok_type, tok_val = FindLongestMatch(OUTER_RE, ' "foo"', 1)
    self.assertEqual(e, 2)
    self.assertEqual(tok_type, LEFT_D_QUOTE)
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
