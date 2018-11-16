#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
cmd_exec_test.py: Tests for cmd_exec.py
"""

import unittest

from core import state
from core import test_lib

from osh.meta import ast, Id
from osh import parse_lib


def InitCommandParser(code_str, arena=None):
  arena = arena or test_lib.MakeArena('<cmd_exec_test.py>')
  parse_ctx = parse_lib.ParseContext(arena, {})
  line_reader, lexer = parse_lib.InitLexer(code_str, arena)
  _, c_parser = parse_ctx.MakeOshParser(line_reader)
  return c_parser


def InitEvaluator():
  word_ev = test_lib.MakeTestEvaluator()
  state.SetLocalString(word_ev.mem, 'x', 'xxx')
  state.SetLocalString(word_ev.mem, 'y', 'yyy')
  return word_ev


class ExpansionTest(unittest.TestCase):

  def testBraceExpand(self):
    # TODO: Move this to test_lib?
    c_parser = InitCommandParser('echo _{a,b}_')
    node = c_parser._ParseCommandLine()
    print(node)

    arena = test_lib.MakeArena('<cmd_exec_test.py>')
    ex = test_lib.InitExecutor(arena)
    #print(ex.Execute(node))

    #print(ex._ExpandWords(node.words))


class VarOpTest(unittest.TestCase):

  def testVarOps(self):
    ev = InitEvaluator()  # initializes x=xxx and y=yyy
    unset_sub = ast.BracedVarSub(ast.token(Id.VSub_Name, 'unset'))
    part_vals = []
    ev._EvalWordPart(unset_sub, part_vals)
    print(part_vals)

    set_sub = ast.BracedVarSub(ast.token(Id.VSub_Name, 'x'))
    part_vals = []
    ev._EvalWordPart(set_sub, part_vals)
    print(part_vals)

    # Now add some ops
    part = ast.LiteralPart(ast.token(Id.Lit_Chars, 'default'))
    arg_word = ast.CompoundWord([part])
    test_op = ast.StringUnary(Id.VTest_ColonHyphen, arg_word)
    unset_sub.suffix_op = test_op
    set_sub.suffix_op = test_op

    part_vals = []
    ev._EvalWordPart(unset_sub, part_vals)
    print(part_vals)

    part_vals = []
    ev._EvalWordPart(set_sub, part_vals)
    print(part_vals)


if __name__ == '__main__':
  unittest.main()
