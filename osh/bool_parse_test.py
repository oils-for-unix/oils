#!/usr/bin/env python2
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

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import bool_expr_e
from _devbuild.gen.types_asdl import lex_mode_e
from core import test_lib
from osh import bool_parse  # module under test


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
  w_parser = test_lib.InitWordParser(code_str + ' ]]', arena=arena)
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
    self.assertEqual(bool_expr_e.Unary, node.tag)

    p = _MakeParser('foo == bar')
    node = p.ParseFactor()
    print(node)
    self.assertTrue(p._TestAtEnd())
    self.assertEqual(bool_expr_e.Binary, node.tag)

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
    self.assertEqual(bool_expr_e.Binary, node.tag)

  def testParseParenthesized(self):
    p = _MakeParser('zoo && ( foo == bar )')
    node = p.ParseExpr()
    print(node)
    self.assertEqual(bool_expr_e.LogicalAnd, node.tag)


if __name__ == '__main__':
  unittest.main()
