#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
from __future__ import print_function
"""
completion_test.py: Tests for completion.py
"""

import unittest
import sys

from core import alloc
from core import cmd_exec_test
from core import completion  # module under test
from core import state
from core import test_lib
from core import ui
from core import util
from osh.meta import Id

from osh.meta import ast
from osh import parse_lib

assign_op_e = ast.assign_op_e


A1 = completion.WordsAction(['foo.py', 'foo', 'bar.py'])

C1 = completion.ChainedCompleter([A1])

mem = state.Mem('', [], {}, None)
exec_opts = state.ExecOpts(mem, None)
debug_f = util.DebugFile(sys.stdout)
progress_f = ui.TestStatusLine()


V1 = completion.WordsAction(['$var1', '$var2', '$another_var'])

EMPTY = completion.WordsAction(['grep', 'sed', 'test'])
FIRST = completion.WordsAction(['grep', 'sed', 'test'])


class CompletionTest(unittest.TestCase):

  def testLookup(self):
    c = completion.CompletionLookup()
    c.RegisterName('grep', C1)
    print(c.GetCompleterForName('grep'))
    print(c.GetCompleterForName('/usr/bin/grep'))

    c.RegisterGlob('*.py', C1)
    comp = c.GetCompleterForName('/usr/bin/foo.py')
    print('py', comp)
    # NOTE: This is an implementation detail
    self.assertEqual(1, len(comp.actions))

    comp_rb = c.GetCompleterForName('foo.rb')
    print('rb', comp_rb)
    # NOTE: This is an implementation detail
    self.assertEqual(0, len(comp_rb.actions))

  def testWordsAction(self):
    print(list(A1.Matches(['f'], 0, 'f')))

  def testExternalCommandAction(self):
    mem = state.Mem('dummy', [], {}, None)
    a = completion.ExternalCommandAction(mem)
    print(list(a.Matches([], 0, 'f')))

  def testShellFuncExecution(self):
    ex = cmd_exec_test.InitExecutor()
    func_node = ast.FuncDef()

    c1 = ast.CompoundWord()
    t1 = ast.token(Id.Lit_Chars, 'f1')
    c1.parts.append(ast.LiteralPart(t1))
    c1.spids.append(0)

    c2 = ast.CompoundWord()
    t2 = ast.token(Id.Lit_Chars, 'f2')
    c2.parts.append(ast.LiteralPart(t2))

    a = ast.ArrayLiteralPart()
    a.words = [c1, c2]
    w = ast.CompoundWord()
    w.parts.append(a)

    # Set global COMPREPLY=(f1 f2)
    pair = ast.assign_pair(ast.LhsName('COMPREPLY'), assign_op_e.Equal, w)
    pair.spids.append(0)  # dummy
    pairs = [pair]
    body_node = ast.Assignment(Id.Assign_None, [], pairs)
    #body_node.spids.append(0)  # dummy

    func_node.name = 'myfunc'
    func_node.body = body_node

    a = completion.ShellFuncAction(ex, func_node)
    matches = list(a.Matches([], 0, 'f'))
    self.assertEqual(['f1 ', 'f2 '], matches)

  def testChainedCompleter(self):
    matches = list(C1.Matches(['f'], 0, 'f'))
    self.assertEqual(['foo.py ', 'foo '], matches)

    p = completion.GlobPredicate('*.py')
    c2 = completion.ChainedCompleter([A1], predicate=p)
    matches = list(c2.Matches(['f'], 0, 'f'))
    self.assertEqual([], matches)

  def testRootCompleter(self):
    comp_lookup = completion.CompletionLookup()

    comp_lookup.RegisterName('grep', C1)
    comp_lookup.RegisterEmpty(EMPTY)
    comp_lookup.RegisterFirst(FIRST)

    ev = test_lib.MakeTestEvaluator()

    pool = alloc.Pool()
    arena = pool.NewArena()
    parse_ctx = parse_lib.ParseContext(arena, {})
    var_comp = V1
    r = completion.RootCompleter(pool, ev, comp_lookup, var_comp, parse_ctx,
                                 progress_f, debug_f)

    m = list(r.Matches('grep f'))
    self.assertEqual(['foo.py ', 'foo '], m)

    m = list(r.Matches('grep g'))
    self.assertEqual([], m)

    m = list(r.Matches('ls $v'))
    self.assertEqual(['$var1 ', '$var2 '], m)

    m = list(r.Matches('g'))
    self.assertEqual(['grep '], m)

    # Empty completer
    m = list(r.Matches(''))
    self.assertEqual(['grep ', 'sed ', 'test '], m)

    # Test compound commands. These PARSE
    m = list(r.Matches('echo hi || grep f'))
    m = list(r.Matches('echo hi; grep f'))

    # Brace -- does NOT parse
    m = list(r.Matches('{ echo hi; grep f'))
    # TODO: Test if/for/while/case/etc.

    m = list(r.Matches('var=$v'))
    m = list(r.Matches('local var=$v'))


def _TestGetCompletionType(buf):
  ev = test_lib.MakeTestEvaluator()
  arena = test_lib.MakeArena('<completion_test.py>')
  parse_ctx = parse_lib.ParseContext(arena, {})
  w_parser, c_parser = parse_ctx.MakeParserForCompletion(buf, arena)
  print('---', buf)
  return completion._GetCompletionType(w_parser, c_parser, ev, debug_f)


f = _TestGetCompletionType


class PartialParseTest(unittest.TestCase):

  def testEmpty(self):
    print(f(''))
    print(f(' '))

  def testCommands(self):
    # External
    print(f('ls'))
    print(f('ls '))

    # Redirect
    print(f('cat <'))
    print(f('cat <input'))

    # Builtin
    print(f('time'))
    print(f('time '))
    print(f('time echo'))

    # Pipeline
    print(f('ls |'))
    print(f('ls | wc -l'))

    # AndOr
    print(f('ls && '))
    print(f('ls && echo'))

    # List
    print(f('echo a;'))
    print(f('echo a; echo'))

    # BraceGroup
    print(f('{ echo hi;'))
    print(f('{ echo hi; echo'))  # second word
    print(f('{ echo hi; echo bye;'))  # new command

    # Subshell
    print(f('( echo hi'))
    print(f('( echo hi; echo'))

    # FunctionDef
    print(f('f() {'))
    print(f('f() { echo'))
    print(f('f() { echo hi;'))

    print(f('if'))
    print(f('if '))
    print(f('if test '))

    print(f('while'))
    print(f('while '))
    print(f('while test '))

    print(f('case $foo '))  # in
    print(f('case $foo in a)'))
    print(f('case $foo in a) echo'))

  def testVarSub(self):
    # TODO: Mem needs variable "f"

    # BracedVarSub
    print(f('echo $'))
    print(f('echo $f'))

    # Double Quoted BracedVarSub
    print(f('echo "$'))
    print(f('echo "$f'))

    # Braced var sub
    #print(f('echo ${'))  # TODO: FIx bug
    #print(f('echo ${f'))

    # Quoted Braced var sub
    #print(f('echo "${'))
    #print(f('echo "${f'))

    # Single quoted var sub should give nothing
    print(f("echo '${"))
    print(f("echo '${f"))

    # Array index
    #print(f('echo ${a['))
    #print(f('echo ${a[k'))

    # Var sub in command sub
    print(f('echo $(ls $'))
    print(f('echo $(ls $f'))

    # Var sub in var sub (bash doesn't do this)
    #print(f('echo ${a:-$'))
    #print(f('echo ${a:-$f'))

  def testCommandSub(self):

    # CommandSubPart
    print(f('echo $('))
    print(f('echo $(ls '))
    print(f('echo $(ls foo'))

    #print(f('echo `'))
    #print(f('echo `ls '))

    # Command sub in var sub
    #print(f('echo ${a:-$('))
    #print(f('echo ${a:-$(l'))

  def testArithSub(self):
    pass

    # BONUS points: ArithSubPart
    #print(f('echo $((a'))
    #print(f('echo $(($a'))

if __name__ == '__main__':
  unittest.main()
