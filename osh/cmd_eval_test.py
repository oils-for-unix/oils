#!/usr/bin/env python2
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
cmd_eval_test.py: Tests for cmd_eval.py
"""

import unittest

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import (
    braced_var_sub, suffix_op, compound_word
)
from core import test_lib
from core.test_lib import Tok


def InitEvaluator():
  word_ev = test_lib.InitWordEvaluator()
  test_lib.SetLocalString(word_ev.mem, 'x', 'xxx')
  test_lib.SetLocalString(word_ev.mem, 'y', 'yyy')
  return word_ev


class ExpansionTest(unittest.TestCase):

  def testBraceExpand(self):
    arena = test_lib.MakeArena('<cmd_eval_test.py>')
    c_parser = test_lib.InitCommandParser('echo _{a,b}_', arena=arena)
    node = c_parser._ParseCommandLine()
    print(node)

    cmd_ev = test_lib.InitCommandEvaluator(arena=arena)
    #print(cmd_ev.Execute(node))
    #print(cmd_ev._ExpandWords(node.words))


class VarOpTest(unittest.TestCase):

  def testVarOps(self):
    ev = InitEvaluator()  # initializes x=xxx and y=yyy
    left = None
    unset_sub = braced_var_sub(left, Tok(Id.VSub_Name, 'unset'))
    part_vals = []
    ev._EvalWordPart(unset_sub, part_vals, 0)
    print(part_vals)

    set_sub = braced_var_sub(left, Tok(Id.VSub_Name, 'x'))
    part_vals = []
    ev._EvalWordPart(set_sub, part_vals, 0)
    print(part_vals)

    # Now add some ops
    part = Tok(Id.Lit_Chars, 'default')
    arg_word = compound_word([part])
    op_tok = Tok(Id.VTest_ColonHyphen, ':-')
    test_op = suffix_op.Unary(op_tok, arg_word)
    unset_sub.suffix_op = test_op
    set_sub.suffix_op = test_op

    part_vals = []
    ev._EvalWordPart(unset_sub, part_vals, 0)
    print(part_vals)

    part_vals = []
    ev._EvalWordPart(set_sub, part_vals, 0)
    print(part_vals)


if __name__ == '__main__':
  unittest.main()
