#!/usr/bin/env python
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

from asdl import const

from core import alloc
from core import test_lib
from core import word
from core import util

from osh.meta import ast, Id, types
from osh import ast_lib
from osh import parse_lib
from osh.word_parse import WordParser  # module under test

arith_expr_e = ast.arith_expr_e
lex_mode_e = types.lex_mode_e


def _InitWordParserWithArena(s):
  pool = alloc.Pool()
  arena = pool.NewArena()
  arena.PushSource('word_parse_test.py')
  line_reader, lexer = parse_lib.InitLexer(s, arena)
  w_parser = WordParser(lexer, line_reader)
  return arena, w_parser


def InitWordParser(s):
  _, w_parser = _InitWordParserWithArena(s)
  return w_parser


def _assertReadWordWithArena(test, word_str):
  print('\n---', word_str)
  arena, w_parser = _InitWordParserWithArena(word_str)
  w = w_parser.ReadWord(lex_mode_e.OUTER)
  if w:
    ast_lib.PrettyPrint(w)
  else:
    err = w_parser.Error()
    test.fail("Couldn't parse %r: %s" % (word_str, err))

  # Next word must be Eof_Real
  w2 = w_parser.ReadWord(lex_mode_e.OUTER)
  test.assertTrue(
      test_lib.TokenWordsEqual(ast.TokenWord(ast.token(Id.Eof_Real, '')), w2),
      w2)

  return arena, w


def _assertReadWord(test, word_str):
  _, w = _assertReadWordWithArena(test, word_str)
  return w


def _assertSpanForWord(test, code_str):
  arena, w = _assertReadWordWithArena(test, code_str)
  span_id = word.LeftMostSpanForWord(w)

  print(code_str)
  print(span_id)

  if span_id != const.NO_INTEGER:
    span = arena.GetLineSpan(span_id)
    print(span)


def _assertReadWordFailure(test, word_str):
  print('\n---', word_str)
  w_parser = InitWordParser(word_str)
  try:
    w = w_parser.ReadWord(lex_mode_e.OUTER)
  except util.ParseError as e:
    print(e)
    return
  if not w:
    print(w_parser.Error())
    return

  ast_lib.PrettyPrint(w)
  test.fail('Expected a parser error, got %r' % w)


def _GetSuffixOp(test, w):
  """Get a single transform op"""
  test.assertEqual(1, len(w.parts))
  return w.parts[0].suffix_op


def _GetPrefixOp(test, w):
  """Get a single transform op"""
  test.assertEqual(1, len(w.parts))
  return w.parts[0].prefix_op


def _GetVarSub(test, w):
  """Get a single transform op"""
  test.assertEqual(1, len(w.parts))
  return w.parts[0]


class WordParserTest(unittest.TestCase):

  def testStaticEvalWord(self):
    expr = r'\EOF'  # Quoted here doc delimiter
    w_parser = InitWordParser(expr)
    w = w_parser.ReadWord(lex_mode_e.OUTER)
    ok, s, quoted = word.StaticEval(w)
    self.assertEqual(True, ok)
    self.assertEqual('EOF', s)
    self.assertEqual(True, quoted)

  def testDisambiguatePrefix(self):
    w = _assertReadWord(self, '${#}')
    self.assertEqual('#', _GetVarSub(self, w).token.val)
    w = _assertReadWord(self, '${!}')
    self.assertEqual('!', _GetVarSub(self, w).token.val)
    w = _assertReadWord(self, '${?}')
    self.assertEqual('?', _GetVarSub(self, w).token.val)

    w = _assertReadWord(self, '${var}')

    w = _assertReadWord(self, '${15}')

    w = _assertReadWord(self, '${#var}')
    self.assertEqual(Id.VSub_Pound, _GetPrefixOp(self, w))
    w = _assertReadWord(self, '${!ref}')
    self.assertEqual(Id.VSub_Bang, _GetPrefixOp(self, w))

    # Length of length
    w = _assertReadWord(self, '${##}')
    self.assertEqual('#', _GetVarSub(self, w).token.val)
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
    self.assertEqual(Id.VOp1_Pound, _GetSuffixOp(self, w).op_id)

    w = _assertReadWord(self, '${!var#prefix}')
    self.assertEqual(1, len(w.parts))
    self.assertEqual(Id.VSub_Bang, _GetPrefixOp(self, w))
    self.assertEqual(Id.VOp1_Pound, _GetSuffixOp(self, w).op_id)

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

  def assertUnquoted(self, expected, w):
    ok, s, quoted = word.StaticEval(w)
    self.assertTrue(ok)
    self.assertEqual(expected, s)
    self.assertFalse(quoted)

  def testPatSub(self):
    w = _assertReadWord(self, '${var/pat/replace}')
    op = _GetSuffixOp(self, w)
    self.assertFalse(op.do_all)
    self.assertFalse(op.do_prefix)
    self.assertFalse(op.do_suffix)
    self.assertUnquoted('pat', op.pat)
    self.assertUnquoted('replace', op.replace)

    w = _assertReadWord(self, '${var//pat/replace}')  # sub all
    op = _GetSuffixOp(self, w)
    self.assertTrue(op.do_all)
    self.assertUnquoted('pat', op.pat)
    self.assertUnquoted('replace', op.replace)

    w = _assertReadWord(self, '${var/%pat/replace}')  # prefix
    op = _GetSuffixOp(self, w)
    self.assertTrue(op.do_suffix)
    self.assertUnquoted('pat', op.pat)
    self.assertUnquoted('replace', op.replace)

    w = _assertReadWord(self, '${var/#pat/replace}')  # suffix
    op = _GetSuffixOp(self, w)
    self.assertTrue(op.do_prefix)
    self.assertUnquoted('pat', op.pat)
    self.assertUnquoted('replace', op.replace)

    w = _assertReadWord(self, '${var/pat}')  # no replacement
    w = _assertReadWord(self, '${var//pat}')  # no replacement
    op = _GetSuffixOp(self, w)
    self.assertTrue(op.do_all)
    self.assertUnquoted('pat', op.pat)
    self.assertEqual(None, op.replace)

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

    ok, s, quoted = word.StaticEval(op.replace)
    self.assertTrue(ok)
    self.assertEqual('//', s)
    self.assertTrue(quoted)

    # Real example found in the wild!
    # http://www.oilshell.org/blog/2016/11/07.html
    w = _assertReadWord(self, r'${var////\\/}')
    op = _GetSuffixOp(self, w)
    self.assertTrue(op.do_all)

    self.assertUnquoted('/', op.pat)

    ok, s, quoted = word.StaticEval(op.replace)
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
    self.assertTrue(Id.VOp1_Pound, _GetSuffixOp(self, w).op_id)
    w = _assertReadWord(self, '${var#prefix}')
    self.assertTrue(Id.VOp1_Pound, _GetSuffixOp(self, w).op_id)

    w = _assertReadWord(self, '${var##}')
    self.assertTrue(Id.VOp1_DPound, _GetSuffixOp(self, w).op_id)
    w = _assertReadWord(self, '${var##prefix}')
    self.assertTrue(Id.VOp1_DPound, _GetSuffixOp(self, w).op_id)

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
        w = w_parser.ReadWord(lex_mode_e.OUTER)
        if w is None:
          e = w_parser.Error()
          print('Error in word parser: %s' % e)
          self.fail(e)

        ast_lib.PrettyPrint(w)

        if word.CommandId(w) == Id.Eof_Real:
          break

  def testReadComment(self):
    # Test that we get Id.Op_Newline
    code = 'foo # comment\nbar #comment\n'
    w_parser = InitWordParser(code)
    w = w_parser.ReadWord(lex_mode_e.OUTER)
    assert w
    self.assertEqual('foo', w.parts[0].token.val)

    w = w_parser.ReadWord(lex_mode_e.OUTER)
    assert w
    self.assertEqual(Id.Op_Newline, w.token.id)

    w = w_parser.ReadWord(lex_mode_e.OUTER)
    assert w
    self.assertEqual('bar', w.parts[0].token.val)

    w = w_parser.ReadWord(lex_mode_e.OUTER)
    assert w
    self.assertEqual(Id.Op_Newline, w.token.id)

    w = w_parser.ReadWord(lex_mode_e.OUTER)
    assert w
    self.assertEqual(Id.Eof_Real, w.token.id)

  def testReadRegex(self):
    # Test that we get Id.Op_Newline
    code = '(foo|bar)'
    w_parser = InitWordParser(code)
    w_parser.next_lex_mode = lex_mode_e.BASH_REGEX  # needed at beginning

    w = w_parser.ReadWord(lex_mode_e.BASH_REGEX)
    assert w
    self.assertEqual('(', w.parts[0].token.val)
    self.assertEqual('foo', w.parts[1].token.val)
    self.assertEqual('|', w.parts[2].token.val)
    self.assertEqual('bar', w.parts[3].token.val)
    self.assertEqual(')', w.parts[4].token.val)
    self.assertEqual(5, len(w.parts))

    w = w_parser.ReadWord(lex_mode_e.OUTER)
    assert w
    self.assertEqual(Id.Eof_Real, w.token.id)

  def testReadArithWord(self):
    w = _assertReadWord(self, '$(( f(x) ))')
    child = w.parts[0].anode
    self.assertEqual(arith_expr_e.FuncCall, child.tag)

    w = _assertReadWord(self, '$(( f(1, 2, 3, 4) ))')
    child = w.parts[0].anode
    self.assertEqual(arith_expr_e.FuncCall, child.tag)
    self.assertEqual(4, len(child.args))

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
      w_parser._Next(lex_mode_e.ARITH)  # Can we remove this requirement?

      while True:
        w = w_parser.ReadWord(lex_mode_e.ARITH)
        if not w:
          err = w_parser.Error()
          print('ERROR', err)
          self.fail(err)
          break
        ast_lib.PrettyPrint(w)
        if word.CommandId(w) in (Id.Eof_Real, Id.Unknown_Tok):
          break

  def testMultiLine(self):
    w_parser = InitWordParser("""\
ls foo

# Multiple newlines and comments should be ignored

ls bar
""")
    print('--MULTI')
    w = w_parser.ReadWord(lex_mode_e.OUTER)
    parts = [ast.LiteralPart(ast.token(Id.Lit_Chars, 'ls'))]
    test_lib.AssertAsdlEqual(self, ast.CompoundWord(parts), w)

    w = w_parser.ReadWord(lex_mode_e.OUTER)
    parts = [ast.LiteralPart(ast.token(Id.Lit_Chars, 'foo'))]
    test_lib.AssertAsdlEqual(self, ast.CompoundWord(parts), w)

    w = w_parser.ReadWord(lex_mode_e.OUTER)
    t = ast.token(Id.Op_Newline, '\n')
    test_lib.AssertAsdlEqual(self, ast.TokenWord(t), w)

    w = w_parser.ReadWord(lex_mode_e.OUTER)
    parts = [ast.LiteralPart(ast.token(Id.Lit_Chars, 'ls'))]
    test_lib.AssertAsdlEqual(self, ast.CompoundWord(parts), w)

    w = w_parser.ReadWord(lex_mode_e.OUTER)
    parts = [ast.LiteralPart(ast.token(Id.Lit_Chars, 'bar'))]
    test_lib.AssertAsdlEqual(self, ast.CompoundWord(parts), w)

    w = w_parser.ReadWord(lex_mode_e.OUTER)
    t = ast.token(Id.Op_Newline, '\n')
    test_lib.AssertAsdlEqual(self, ast.TokenWord(t), w)

    w = w_parser.ReadWord(lex_mode_e.OUTER)
    t = ast.token(Id.Eof_Real, '')
    test_lib.AssertAsdlEqual(self, ast.TokenWord(t), w)

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
