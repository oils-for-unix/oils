#!/usr/bin/python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
completion_test.py: Tests for completion.py
"""

import unittest

from core import cmd_exec
from core import cmd_exec_test
from core import completion  # module under test
from core import lexer
from core import state
from core import word_eval
from core import ui
from core.id_kind import Id

from osh import ast_ as ast
from osh import parse_lib


A1 = completion.WordsAction(['foo.py', 'foo', 'bar.py'])

C1 = completion.ChainedCompleter([A1])

STATUS = [ui.TestStatusLine()] * 10  # A bunch of dummies

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
    print(c.GetCompleterForName('/usr/bin/foo.py'))

    print(c.GetCompleterForName('foo.rb'))

  def testWordsAction(self):
    print(list(A1.Matches(['f'], 0, 'f')))

  def testExternalCommandAction(self):
    mem = state.Mem('dummy', [], {})
    a = completion.ExternalCommandAction(mem)
    print(list(a.Matches([], 0, 'f')))

  def testShellFuncExecution(self):
    ex = cmd_exec_test.InitExecutor()
    func_node = ast.FuncDef()

    c1 = ast.CompoundWord()
    t1 = ast.token(Id.Lit_Chars, 'f1')
    c1.parts.append(ast.LiteralPart(t1))

    c2 = ast.CompoundWord()
    t2 = ast.token(Id.Lit_Chars, 'f2')
    c2.parts.append(ast.LiteralPart(t2))

    a = ast.ArrayLiteralPart()
    a.words = [c1, c2]
    w = ast.CompoundWord()
    w.parts.append(a)

    # Set global COMPREPLY=(f1 f2)
    pairs = [ast.assign_pair(ast.LhsName('COMPREPLY'), w)]
    body_node = ast.Assignment(Id.Assign_None, pairs)

    func_node.body = body_node

    a = completion.ShellFuncAction(ex, func_node)
    matches = list(a.Matches([], 0, 'f'))
    self.assertEqual(['f1 ', 'f2 '], matches)

  def testChainedCompleter(self):
    print(list(C1.Matches(['f'], 0, 'f')))

    p = completion.GlobPredicate('*.py')
    c2 = completion.ChainedCompleter([A1], predicate=p)
    print(list(c2.Matches(['f'], 0, 'f')))

  def testRootCompleter(self):
    comp_lookup = completion.CompletionLookup()

    comp_lookup.RegisterName('grep', C1)
    comp_lookup.RegisterEmpty(EMPTY)
    comp_lookup.RegisterFirst(FIRST)

    ev = _MakeTestEvaluator()

    var_comp = V1
    r = completion.RootCompleter(parse_lib.MakeParserForCompletion,
        ev, comp_lookup, var_comp)

    m = list(r.Matches('grep f', STATUS))
    self.assertEqual(['foo.py ', 'foo '], m)

    m = list(r.Matches('grep g', STATUS))
    self.assertEqual([], m)

    m = list(r.Matches('ls $v', STATUS))
    self.assertEqual(['$var1 ', '$var2 '], m)

    m = list(r.Matches('g', STATUS))
    self.assertEqual(['grep '], m)

    # Empty completer
    m = list(r.Matches('', STATUS))
    self.assertEqual(['grep ', 'sed ', 'test '], m)

    # Test compound commands. These PARSE
    m = list(r.Matches('echo hi || grep f', STATUS))
    m = list(r.Matches('echo hi; grep f', STATUS))

    # Brace -- does NOT parse
    m = list(r.Matches('{ echo hi; grep f', STATUS))
    # TODO: Test if/for/while/case/etc.

    m = list(r.Matches('var=$v', STATUS))
    m = list(r.Matches('local var=$v', STATUS))


def _MakeTestEvaluator():
  mem = state.Mem('', [], {})
  exec_opts = state.ExecOpts()
  ev = word_eval.CompletionWordEvaluator(mem, exec_opts)
  return ev


def _TestGetCompletionType(buf):
  ev = _MakeTestEvaluator()
  w_parser, c_parser = parse_lib.MakeParserForCompletion(buf)
  print('---', buf)
  return completion._GetCompletionType(w_parser, c_parser, ev, STATUS)


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
