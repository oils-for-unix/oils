#!/usr/bin/env python2
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

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import suffix_op, word_part, token
from _devbuild.gen.syntax_asdl import word
from core import test_lib
from osh import state


def InitEvaluator():
  word_ev = test_lib.MakeTestEvaluator()
  state.SetLocalString(word_ev.mem, 'x', 'xxx')
  state.SetLocalString(word_ev.mem, 'y', 'yyy')
  return word_ev


class ExpansionTest(unittest.TestCase):

  def testBraceExpand(self):
    arena = test_lib.MakeArena('<cmd_exec_test.py>')
    c_parser = test_lib.InitCommandParser('echo _{a,b}_', arena=arena)
    node = c_parser._ParseCommandLine()
    print(node)

    ex = test_lib.InitExecutor(arena=arena)
    #print(ex.Execute(node))
    #print(ex._ExpandWords(node.words))


class VarOpTest(unittest.TestCase):

  def testVarOps(self):
    ev = InitEvaluator()  # initializes x=xxx and y=yyy
    unset_sub = word_part.BracedVarSub(token(Id.VSub_Name, 'unset'))
    part_vals = []
    ev._EvalWordPart(unset_sub, part_vals)
    print(part_vals)

    set_sub = word_part.BracedVarSub(token(Id.VSub_Name, 'x'))
    part_vals = []
    ev._EvalWordPart(set_sub, part_vals)
    print(part_vals)

    # Now add some ops
    part = word_part.Literal(token(Id.Lit_Chars, 'default'))
    arg_word = word.CompoundWord([part])
    test_op = suffix_op.StringUnary(Id.VTest_ColonHyphen, arg_word)
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
