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
import sys

from core import cmd_exec  # module under test
from core import dev
from core import legacy
from core import word_eval
from core import process
from core import state
from core import test_lib
from core import util

from osh.meta import ast, Id
from osh import parse_lib


def InitCommandParser(code_str):
  arena = test_lib.MakeArena('<cmd_exec_test.py>')
  parse_ctx = parse_lib.ParseContext(arena, {})
  line_reader, lexer = parse_lib.InitLexer(code_str, arena)
  _, c_parser = parse_ctx.MakeParser(line_reader)
  return c_parser


def InitExecutor(arena=None):
  arena = arena or test_lib.MakeArena('<InitExecutor>')

  mem = state.Mem('', [], {}, arena)
  fd_state = process.FdState()
  funcs = {}
  comp_funcs = {}
  # For the tests, we do not use 'readline'.
  exec_opts = state.ExecOpts(mem, None)
  parse_ctx = parse_lib.ParseContext(arena, {})

  debug_f = util.DebugFile(sys.stderr)
  devtools = dev.DevTools(dev.CrashDumper(''), debug_f, debug_f)

  return cmd_exec.Executor(mem, fd_state, funcs, comp_funcs, exec_opts,
                           parse_ctx, devtools)


def InitEvaluator():
  mem = state.Mem('', [], {}, None)
  state.SetLocalString(mem, 'x', 'xxx')
  state.SetLocalString(mem, 'y', 'yyy')

  exec_opts = state.ExecOpts(mem, None)
  # Don't need side effects for most things
  splitter = legacy.SplitContext(mem)
  return word_eval.CompletionWordEvaluator(mem, exec_opts, splitter)


class ExpansionTest(unittest.TestCase):

  def testBraceExpand(self):
    # TODO: Move this to test_lib?
    c_parser = InitCommandParser('echo _{a,b}_')
    node = c_parser._ParseCommandLine()
    print(node)

    arena = test_lib.MakeArena('<cmd_exec_test.py>')
    ex = InitExecutor(arena)
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
