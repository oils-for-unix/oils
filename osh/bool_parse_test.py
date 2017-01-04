#!/usr/bin/env python3
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

from core.id_kind import Id

from osh import ast_ as ast
from osh import parse_lib
from osh import bool_parse  # module under test
from osh.lex import LexMode

bool_expr_e = ast.bool_expr_e


def _ReadWords(w_parser):
  words = []
  while True:
    w = w_parser.ReadWord(LexMode.DBRACKET)
    if w.Type() == Id.Eof_Real:
      break
    words.append(w)
  print('')
  print('words:', words)

  return words


def _MakeParser(code_str):
  # NOTE: We need the extra ]] token
  w_parser, _ = parse_lib.MakeParserForCompletion(code_str + ' ]]')
  w_parser._Next(LexMode.DBRACKET)  # for tests only
  p = bool_parse.BoolParser(w_parser)
  if not p._Next():
    raise AssertionError
  return p


class BoolParserTest(unittest.TestCase):

  def testParseFactor(self):
    p = _MakeParser('foo')
    print(p.ParseFactor())
    self.assertTrue(p.AtEnd())

    p = _MakeParser('$foo"bar"')
    print(p.ParseFactor())
    self.assertTrue(p.AtEnd())

    p = _MakeParser('-z foo')
    print('-------------')
    node = p.ParseFactor()
    print(node)
    self.assertTrue(p.AtEnd())
    self.assertEqual(bool_expr_e.BoolUnary, node.tag)

    p = _MakeParser('foo == bar')
    node = p.ParseFactor()
    print(node)
    self.assertTrue(p.AtEnd())
    self.assertEqual(bool_expr_e.BoolBinary, node.tag)

  def testParseNegatedFactor(self):
    p = _MakeParser('foo')
    node = p.ParseNegatedFactor()
    print(node)
    self.assertTrue(p.AtEnd())
    self.assertEqual(bool_expr_e.WordTest, node.tag)

    p = _MakeParser('! foo')
    node = p.ParseNegatedFactor()
    print(node)
    self.assertTrue(p.AtEnd())
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
    self.assertTrue(p.AtEnd())
    self.assertEqual(bool_expr_e.BoolBinary, node.tag)

  def testParseParenthesized(self):
    p = _MakeParser('zoo && ( foo == bar )')
    node = p.ParseExpr()
    print(node)
    self.assertEqual(bool_expr_e.LogicalAnd, node.tag)


if __name__ == '__main__':
  unittest.main()
