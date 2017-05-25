#!/usr/bin/python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
cmd_exec_test.py: Tests for cmd_exec.py
"""

import os
import unittest

from core.builtin import Builtins
from core import cmd_exec  # module under test
from core.cmd_exec import *
from core.id_kind import Id
from core import completion
from core import ui
from core import word_eval
from core import runtime
from core import process

from osh import ast_ as ast
from osh import parse_lib


def InitCommandParser(code_str):
  from osh.word_parse import WordParser
  from osh.cmd_parse import CommandParser
  line_reader, lexer = parse_lib.InitLexer(code_str)
  w_parser = WordParser(lexer, line_reader)
  c_parser = CommandParser(w_parser, lexer, line_reader)
  return c_parser


def InitExecutor():
  mem = cmd_exec.Mem('', [])
  status_line = ui.NullStatusLine()
  builtins = Builtins(status_line)
  funcs = {}
  comp_funcs = {}
  exec_opts = cmd_exec.ExecOpts()
  return cmd_exec.Executor(mem, builtins, funcs, completion, comp_funcs, exec_opts,
                           parse_lib.MakeParserForExecutor)


def InitEvaluator():
  mem = cmd_exec.Mem('', [])

  val1 = runtime.Str('xxx')
  val2 = runtime.Str('yyy')
  pairs = [(ast.LeftVar('x'), val1), (ast.LeftVar('y'), val2)]
  mem.SetLocals(pairs)

  exec_opts = cmd_exec.ExecOpts()
  # Don't need side effects for most things
  return word_eval.CompletionWordEvaluator(mem, exec_opts)


class MemTest(unittest.TestCase):

  def testGet(self):
    mem = cmd_exec.Mem('', [])
    mem.Push(['a', 'b'])
    print(mem.Get('HOME'))
    mem.Pop()
    print(mem.Get('NONEXISTENT'))


class ExpansionTest(unittest.TestCase):

  def testBraceExpand(self):
    # TODO: Move this to test_lib?
    c_parser = InitCommandParser('echo _{a,b}_')
    node = c_parser.ParseCommandLine()
    print(node)

    ex = InitExecutor()
    #print(ex.Execute(node))

    #print(ex._ExpandWords(node.words))


class VarOpTest(unittest.TestCase):

  def testVarOps(self):
    ev = InitEvaluator()  # initializes x=xxx and y=yyy
    unset_sub = ast.BracedVarSub(ast.token(Id.VSub_Name, 'unset'))
    print(ev.part_ev._EvalWordPart(unset_sub))

    set_sub = ast.BracedVarSub(ast.token(Id.VSub_Name, 'x'))
    print(ev.part_ev._EvalWordPart(set_sub))

    # Now add some ops
    part = ast.LiteralPart(ast.token(Id.Lit_Chars, 'default'))
    arg_word = ast.CompoundWord([part])
    test_op = ast.StringUnary(Id.VTest_ColonHyphen, arg_word)
    unset_sub.suffix_op = test_op
    set_sub.suffix_op = test_op

    print(ev.part_ev._EvalWordPart(unset_sub))
    print(ev.part_ev._EvalWordPart(set_sub))


if __name__ == '__main__':
  unittest.main()
