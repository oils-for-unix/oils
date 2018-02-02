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

from core import builtin
from core import cmd_exec  # module under test
from core.cmd_exec import *
from core.id_kind import Id
from core import completion
from core import legacy
from core import word_eval
from core import process
from core import test_lib

from osh import ast_ as ast
from osh import parse_lib


def InitCommandParser(code_str):
  from osh.word_parse import WordParser
  from osh.cmd_parse import CommandParser
  arena = test_lib.MakeArena('<cmd_exec_test.py>')
  line_reader, lexer = parse_lib.InitLexer(code_str, arena)
  w_parser = WordParser(lexer, line_reader)
  c_parser = CommandParser(w_parser, lexer, line_reader, arena)
  return c_parser


def InitExecutor(arena=None):
  if not arena:
    arena = test_lib.MakeArena('<InitExecutor>')

  mem = state.Mem('', [], {}, None)
  fd_state = process.FdState()
  status_lines = None  # not needed for what we're testing
  builtins = builtin.BUILTIN_DEF
  funcs = {}
  comp_funcs = {}
  exec_opts = state.ExecOpts(mem)
  return cmd_exec.Executor(mem, fd_state, status_lines, funcs, completion,
                           comp_funcs, exec_opts, arena)


def InitEvaluator():
  mem = state.Mem('', [], {}, None)
  state.SetLocalString(mem, 'x', 'xxx')
  state.SetLocalString(mem, 'y', 'yyy')

  exec_opts = state.ExecOpts(mem)
  # Don't need side effects for most things
  splitter = legacy.SplitContext(mem)
  return word_eval.CompletionWordEvaluator(mem, exec_opts, splitter)


class ExpansionTest(unittest.TestCase):

  def testBraceExpand(self):
    # TODO: Move this to test_lib?
    c_parser = InitCommandParser('echo _{a,b}_')
    node = c_parser.ParseCommandLine()
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


def ParseAndExecute(code_str):
  arena = test_lib.MakeArena('<shell_test.py>')

  # TODO: Unify with InitCommandParser above.
  from osh.word_parse import WordParser
  from osh.cmd_parse import CommandParser

  line_reader, lexer = parse_lib.InitLexer(code_str, arena)
  w_parser = WordParser(lexer, line_reader)
  c_parser = CommandParser(w_parser, lexer, line_reader, arena)

  node = c_parser.ParseWholeFile()
  if not node:
    raise AssertionError()

  print(node)
  ex = InitExecutor(arena)
  status = ex.Execute(node)

  # TODO: Can we capture output here?
  return status


class ExecutorTest(unittest.TestCase):

  def testBuiltin(self):
    print(ParseAndExecute('echo hi'))


if __name__ == '__main__':
  unittest.main()
