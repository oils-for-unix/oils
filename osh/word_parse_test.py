#!/usr/bin/env python3
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

from core.word_node import LiteralPart, CommandWord, TokenWord
from core.tokens import Id, Token

from osh import parse_lib
from osh.lex import LexMode
from osh.word_parse import WordParser # module under test


def InitWordParser(s):
  line_reader, lexer = parse_lib.InitLexer(s)
  w_parser = WordParser(lexer, line_reader)
  return w_parser


def _assertReadWord(test, word_str):
  print('\n---', word_str)
  w_parser = InitWordParser(word_str)
  w = w_parser.ReadOuter()
  if w:
    print(w)
  else:
    err = w_parser.Error()
    test.fail("Couldn't parse %r: %s" % (word_str, err))

  # Next word must be \n
  w2 = w_parser.ReadOuter()
  test.assertEqual(TokenWord(Token(Id.Op_Newline, '\n')) , w2)

  return w

def _assertReadWordFailure(test, word_str):
  print('\n---', word_str)
  w_parser = InitWordParser(word_str)
  w = w_parser.ReadOuter()
  if w:
    print(w)
    test.fail('Expected a parser error, got %r' % w)
  else:
    print(w_parser.Error())


def _GetTransformOp(test, w):
  """Get a single transform op"""
  test.assertEqual(1, len(w.parts))
  ops = w.parts[0].transform_ops
  test.assertEqual(1, len(ops))
  return ops[0]


def _GetVarSub(test, w):
  """Get a single transform op"""
  test.assertEqual(1, len(w.parts))
  return w.parts[0]


class WordParserTest(unittest.TestCase):

  def testEvalStatic(self):
    expr = r'\EOF'  # Quoted here doc delimiter
    w_parser = InitWordParser(expr)
    w = w_parser.ReadOuter()
    print(w)
    ok, s, quoted = w.EvalStatic()
    self.assertEqual(True, ok)
    self.assertEqual('EOF', s)
    self.assertEqual(True, quoted)

  def testDisambiguatePrefix(self):
    w = _assertReadWord(self, '${#}')
    self.assertEqual('#', _GetVarSub(self, w).name)
    w = _assertReadWord(self, '${!}')
    self.assertEqual('!', _GetVarSub(self, w).name)
    w = _assertReadWord(self, '${?}')
    self.assertEqual('?', _GetVarSub(self, w).name)

    w = _assertReadWord(self, '${var}')

    w = _assertReadWord(self, '${15}')

    w = _assertReadWord(self, '${#var}')
    self.assertEqual(Id.VSub_Pound, _GetTransformOp(self, w).vtype)
    w = _assertReadWord(self, '${!ref}')
    self.assertEqual(Id.VSub_Bang, _GetTransformOp(self, w).vtype)

    # Length of length
    w = _assertReadWord(self, '${##}')
    self.assertEqual('#', _GetVarSub(self, w).name)
    self.assertEqual(Id.VSub_Pound, _GetTransformOp(self, w).vtype)

    w = _assertReadWord(self, '${array[0]}')
    self.assertEqual(1, len(w.parts))
    w = _assertReadWord(self, '${array[@]}')
    self.assertEqual(1, len(w.parts))

    # Length of element
    w = _assertReadWord(self, '${#array[0]}')
    self.assertEqual(1, len(w.parts))
    self.assertEqual(Id.VSub_Pound, _GetTransformOp(self, w).vtype)
    # Ref for element
    w = _assertReadWord(self, '${!array[0]}')
    self.assertEqual(1, len(w.parts))
    self.assertEqual(Id.VSub_Bang, _GetTransformOp(self, w).vtype)

    w = _assertReadWord(self, '${var#prefix}')
    self.assertEqual(1, len(w.parts))
    self.assertEqual(Id.VUnary_Pound, _GetTransformOp(self, w).vtype)

    w = _assertReadWord(self, '${!var#prefix}')
    self.assertEqual(1, len(w.parts))
    # ref op, and prefix op
    self.assertEqual(2, len(w.parts[0].transform_ops))

    _assertReadWordFailure(self, '${#var#prefix}')

    # Allowed by bash, but we don't parse it.  Use len=$#; echo ${len#2}
    # instead.
    _assertReadWordFailure(self, '${##2}')

  def testVarOf(self):
    w = _assertReadWord(self, '${name}')
    w = _assertReadWord(self, '${name[0]}')

    w = _assertReadWord(self, '${array[@]}')

    # Should be DISALLOWED!
    #w = _assertReadWord(self, '${11[@]}')

  def assertUnquoted(self, expected, word):
    ok, s, quoted = word.EvalStatic()
    self.assertTrue(ok)
    self.assertEqual(expected, s)
    self.assertFalse(quoted)

  def testPatSub(self):
    w = _assertReadWord(self, '${var/pat/replace}')
    op = _GetTransformOp(self, w)
    self.assertFalse(op.do_all)
    self.assertFalse(op.do_prefix)
    self.assertFalse(op.do_suffix)
    self.assertUnquoted('pat', op.pat)
    self.assertUnquoted('replace', op.replace)

    w = _assertReadWord(self, '${var//pat/replace}')  # sub all
    op = _GetTransformOp(self, w)
    self.assertTrue(op.do_all)
    self.assertUnquoted('pat', op.pat)
    self.assertUnquoted('replace', op.replace)

    w = _assertReadWord(self, '${var/%pat/replace}')  # prefix
    op = _GetTransformOp(self, w)
    self.assertTrue(op.do_prefix)
    self.assertUnquoted('pat', op.pat)
    self.assertUnquoted('replace', op.replace)

    w = _assertReadWord(self, '${var/#pat/replace}')  # suffix
    op = _GetTransformOp(self, w)
    self.assertTrue(op.do_suffix)
    self.assertUnquoted('pat', op.pat)
    self.assertUnquoted('replace', op.replace)

    w = _assertReadWord(self, '${var/pat}')  # no replacement
    w = _assertReadWord(self, '${var//pat}')  # no replacement
    op = _GetTransformOp(self, w)
    self.assertTrue(op.do_all)
    self.assertUnquoted('pat', op.pat)
    self.assertEqual(None, op.replace)

    # replace with slash
    w = _assertReadWord(self, '${var/pat//}')
    op = _GetTransformOp(self, w)
    self.assertUnquoted('pat', op.pat)
    self.assertUnquoted('/', op.replace)

    # replace with two slashes unquoted
    w = _assertReadWord(self, '${var/pat///}')
    op = _GetTransformOp(self, w)
    self.assertUnquoted('pat', op.pat)
    self.assertUnquoted('//', op.replace)

    # replace with two slashes quoted
    w = _assertReadWord(self, '${var/pat/"//"}')
    op = _GetTransformOp(self, w)
    self.assertUnquoted('pat', op.pat)

    ok, s, quoted = op.replace.EvalStatic()
    self.assertTrue(ok)
    self.assertEqual('//', s)
    self.assertTrue(quoted)

    # Real example found in the wild!
    # http://www.oilshell.org/blog/2016/11/07.html
    w = _assertReadWord(self, r'${var////\\/}')
    op = _GetTransformOp(self, w)
    self.assertTrue(op.do_all)

    self.assertUnquoted('/', op.pat)

    ok, s, quoted = op.replace.EvalStatic()
    self.assertTrue(ok)
    self.assertEqual(r'\/', s)

  def testSlice(self):
    w = _assertReadWord(self, '${foo:0}')
    # No length
    self.assertEqual(None, _GetTransformOp(self, w).length)

    w = _assertReadWord(self, '${foo:0:1}')
    w = _assertReadWord(self, '${foo:1+2:2+3}')

    # This is allowed
    w = _assertReadWord(self, '${foo::1}')
    # No beginning
    self.assertEqual(None, _GetTransformOp(self, w).begin)

  def testLength(self):
    # Synonym for $#, had a bug here
    w = _assertReadWord(self, '${#@}')
    self.assertTrue(Id.VSub_Pound, _GetTransformOp(self, w).vtype)

    # Length of arg 11
    w = _assertReadWord(self, '${#11}')
    self.assertTrue(Id.VSub_Pound, _GetTransformOp(self, w).vtype)

    w = _assertReadWord(self, '${#str}')
    self.assertTrue(Id.VSub_Pound, _GetTransformOp(self, w).vtype)

    w = _assertReadWord(self, '${#array[0]}')
    print(w)
    # BUG!
    #self.assertTrue(VS_POUND, _GetTransformOp(self, w).vtype)

    w = _assertReadWord(self, '${#array["key"]}')
    # BUG!
    #self.assertTrue(Id.VSub_POUND, _GetTransformOp(self, w).vtype)

  def testUnary(self):
    w = _assertReadWord(self, '${var#}')
    self.assertTrue(Id.VUnary_Pound, _GetTransformOp(self, w).vtype)
    w = _assertReadWord(self, '${var#prefix}')
    self.assertTrue(Id.VUnary_Pound, _GetTransformOp(self, w).vtype)

    w = _assertReadWord(self, '${var##}')
    self.assertTrue(Id.VUnary_DPound, _GetTransformOp(self, w).vtype)
    w = _assertReadWord(self, '${var##prefix}')
    self.assertTrue(Id.VUnary_DPound, _GetTransformOp(self, w).vtype)

    w = _assertReadWord(self, '${var%suffix}')
    w = _assertReadWord(self, '${var%%suffix}')

  def testArrayOp(self):
    w = _assertReadWord(self, '${array[0]}')
    w = _assertReadWord(self, '${array[5+5]}')

    w = _assertReadWord(self, '${array[@]}')
    w = _assertReadWord(self, '${array[*]}')

  def testTestOp(self):
    w = _assertReadWord(self, '${var:-default]}')

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
        '${\\\nfoo}',  # VS_1
        '${foo\\\n}',  # VS_2
        '${foo#\\\nyo}',  # VS_ARG_UNQ
        '"${foo#\\\nyo}"',  # VS_ARG_DQ
        ]
    for expr in CASES:
      print('---')
      print(expr)
      print()

      w_parser = InitWordParser(expr)

      while True:
        w = w_parser.ReadOuter()
        if w is None:
          e = w_parser.Error()
          print('Error in word parser: %s' % e)
          self.fail(e)

        print(w)

        if w.Type() == Id.Eof_Real:
          break

  def testReadComment(self):
    # Test that we get Id.Op_Newline
    code = 'foo # comment\nbar #comment\n'
    w_parser = InitWordParser(code)
    w = w_parser.ReadOuter()
    assert w
    self.assertEqual('foo', w.parts[0].token.val)

    w = w_parser.ReadOuter()
    assert w
    self.assertEqual(Id.Op_Newline, w.token.type)

    w = w_parser.ReadOuter()
    assert w
    self.assertEqual('bar', w.parts[0].token.val)

    w = w_parser.ReadOuter()
    assert w
    self.assertEqual(Id.Op_Newline, w.token.type)

    w = w_parser.ReadOuter()
    assert w
    self.assertEqual(Id.Eof_Real, w.token.type)

  def testReadRegex(self):
    # Test that we get Id.Op_Newline
    code = '(foo|bar)'
    w_parser = InitWordParser(code)
    w_parser.next_lex_mode = LexMode.BASH_REGEX  # needed at beginning

    w = w_parser.ReadWord(LexMode.BASH_REGEX)
    assert w
    self.assertEqual('(', w.parts[0].token.val)
    self.assertEqual('foo', w.parts[1].token.val)
    self.assertEqual('|', w.parts[2].token.val)
    self.assertEqual('bar', w.parts[3].token.val)
    self.assertEqual(')', w.parts[4].token.val)
    self.assertEqual(5, len(w.parts))

    w = w_parser.ReadWord(LexMode.OUTER)
    assert w
    self.assertEqual(Id.Op_Newline, w.token.type)

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

      w_parser = InitWordParser(expr)
      w_parser._Next(LexMode.ARITH)  # Can we remove this requirement?

      while True:
        w = w_parser.ReadWord(LexMode.ARITH)
        if not w:
          err = w_parser.Error()
          print('ERROR', err)
          self.fail(err)
          break
        print(w)
        if w.Type() in (Id.Eof_Real, Id.Unknown_Tok):
          break

  def testMultiLine(self):
    w_parser = InitWordParser("""\
ls foo

# Multiple newlines and comments should be ignored

ls bar
""")

    print('--MULTI')
    w = w_parser.ReadOuter()
    parts = [LiteralPart(Token(Id.Lit_Chars, 'ls'))]
    self.assertEqual(CommandWord(parts=parts), w)

    w = w_parser.ReadOuter()
    parts = [LiteralPart(Token(Id.Lit_Chars, 'foo'))]
    self.assertEqual(CommandWord(parts=parts), w)

    w = w_parser.ReadOuter()
    t = Token(Id.Op_Newline, '\n')
    self.assertEqual(TokenWord(t), w)

    w = w_parser.ReadOuter()
    parts = [LiteralPart(Token(Id.Lit_Chars, 'ls'))]
    self.assertEqual(CommandWord(parts=parts), w)

    w = w_parser.ReadOuter()
    parts = [LiteralPart(Token(Id.Lit_Chars, 'bar'))]
    self.assertEqual(CommandWord(parts=parts), w)

    w = w_parser.ReadOuter()
    t = Token(Id.Op_Newline, '\n')
    self.assertEqual(TokenWord(t), w)

    w = w_parser.ReadOuter()
    t = Token(Id.Eof_Real, '')
    self.assertEqual(TokenWord(t), w)


if __name__ == '__main__':
  unittest.main()
