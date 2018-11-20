#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
bool_parse_test.py: Tests for bool_parse.py
"""

import unittest

from core import test_lib
from core.meta import syntax_asdl, Id, types_asdl

from frontend import parse_lib

from osh import bool_parse  # module under test

bool_expr_e = syntax_asdl.bool_expr_e
lex_mode_e = types_asdl.lex_mode_e


def _ReadWords(w_parser):
  words = []
  while True:
    w = w_parser.ReadWord(lex_mode_e.DBracket)
    if w.Type() == Id.Eof_Real:
      break
    words.append(w)
  print('')
  print('words:', words)

  return words


def _MakeParser(code_str):
  # NOTE: We need the extra ]] token
  arena = test_lib.MakeArena('<bool_parse_test.py>')
  parse_ctx = parse_lib.ParseContext(arena, {})
  w_parser, _ = parse_ctx.MakeParserForCompletion(code_str + ' ]]', arena)
  w_parser._Next(lex_mode_e.DBracket)  # for tests only
  p = bool_parse.BoolParser(w_parser)
  p._Next()
  return p


class BoolParserTest(unittest.TestCase):

  def testParseFactor(self):
    p = _MakeParser('foo')
    print(p.ParseFactor())
    self.assertTrue(p._TestAtEnd())

    p = _MakeParser('$foo"bar"')
    print(p.ParseFactor())
    self.assertTrue(p._TestAtEnd())

    p = _MakeParser('-z foo')
    print('-------------')
    node = p.ParseFactor()
    print(node)
    self.assertTrue(p._TestAtEnd())
    self.assertEqual(bool_expr_e.BoolUnary, node.tag)

    p = _MakeParser('foo == bar')
    node = p.ParseFactor()
    print(node)
    self.assertTrue(p._TestAtEnd())
    self.assertEqual(bool_expr_e.BoolBinary, node.tag)

  def testParseNegatedFactor(self):
    p = _MakeParser('foo')
    node = p.ParseNegatedFactor()
    print(node)
    self.assertTrue(p._TestAtEnd())
    self.assertEqual(bool_expr_e.WordTest, node.tag)

    p = _MakeParser('! foo')
    node = p.ParseNegatedFactor()
    print(node)
    self.assertTrue(p._TestAtEnd())
    self.assertEqual(bool_expr_e.LogicalNot, node.tag)

  def testParseTerm(self):
    p = _MakeParser('foo && ! bar')
    node = p.ParseTerm()
    print(node)
    self.assertEqual(bool_expr_e.LogicalAnd, node.tag)

    # TODO: This is an entire expression I guess
    p = _MakeParser('foo && ! bar && baz')
    node = p.ParseTerm()
    print(node)
    self.assertEqual(bool_expr_e.LogicalAnd, node.tag)

    p = _MakeParser('-z foo && -z bar')
    node = p.ParseTerm()
    print(node)
    self.assertEqual(bool_expr_e.LogicalAnd, node.tag)

  def testParseExpr(self):
    p = _MakeParser('foo || ! bar')
    node = p.ParseExpr()
    print(node)
    self.assertEqual(bool_expr_e.LogicalOr, node.tag)

    p = _MakeParser('a == b')
    print(p.ParseExpr())

  def testParseFactorInParens(self):
    p = _MakeParser('( foo == bar )')
    node = p.ParseFactor()
    print(node)
    self.assertTrue(p._TestAtEnd())
    self.assertEqual(bool_expr_e.BoolBinary, node.tag)

  def testParseParenthesized(self):
    p = _MakeParser('zoo && ( foo == bar )')
    node = p.ParseExpr()
    print(node)
    self.assertEqual(bool_expr_e.LogicalAnd, node.tag)


if __name__ == '__main__':
  unittest.main()
