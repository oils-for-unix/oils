#!/usr/bin/env python
# Copyright 2016 Andy Chu. All rights reserved.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
"""
completion_test.py: Tests for completion.py
"""
from __future__ import print_function

import os
import unittest
import sys

from core import alloc
from core import completion  # module under test
from core import test_lib
from core import ui
from core import util
from core.meta import syntax_asdl

from frontend import parse_lib

from osh import state

assign_op_e = syntax_asdl.assign_op_e
log = util.log


A1 = completion.WordsAction(['foo.py', 'foo', 'bar.py'])

C1 = completion.ChainedCompleter([A1])

mem = state.Mem('', [], {}, None)
exec_opts = state.ExecOpts(mem, None)
debug_f = util.DebugFile(sys.stdout)
progress_f = ui.TestStatusLine()


V1 = completion.WordsAction(['$var1', '$var2', '$another_var'])

FIRST = completion.WordsAction(['grep', 'sed', 'test'])


class CompletionTest(unittest.TestCase):
  def _MakeComp(self, words, index, to_complete):
    comp = completion.CompletionApi()
    comp.Update(words=['f'], index=0, to_complete='f')
    return comp

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

  def testWordsAction(self):
    comp = self._MakeComp(['f'], 0, 'f')
    print(list(A1.Matches(comp)))

  def testExternalCommandAction(self):
    mem = state.Mem('dummy', [], {}, None)
    a = completion.ExternalCommandAction(mem)
    comp = self._MakeComp([], 0, 'f')
    print(list(a.Matches(comp)))

  def testFileSystemAction(self):
    a = completion.FileSystemAction()
    # Current dir -- all files and dirs
    comp = self._MakeComp([], 0, '')
    print(list(a.Matches(comp)))

    os.system('mkdir -p /tmp/oil_comp_test')
    os.system('bash -c "touch /tmp/oil_comp_test/{one,two,three}"')

    # TODO: This no longer filters by prefix!
    return

    # This test depends on actual file system content.  But we choose things
    # that shouldn't go away.
    CASES = [
        # Dirs and files
        ('c', ['core/', 'configure']),
        ('nonexistent/', []),
        ('README', ['README.md']),
        # Directory should be completed to core/ ?
        ('core', ['core/']),
        ('asdl/R', ['asdl/README.md']),
        ('opy/doc', ['opy/doc/']),
        ('opy/doc/', ['opy/doc/opcodes.md']),
        ('/bi', ['/bin/']),
        ('/tmp/oil_comp_test/', [
          '/tmp/oil_comp_test/one',
          '/tmp/oil_comp_test/three',
          '/tmp/oil_comp_test/two',
          ])
    ]

    for prefix, expected in CASES:
      log('')
      log('-- PREFIX %s', prefix)
      log('-- expected %s', expected)
      comp = self._MakeComp([], 0, prefix)
      self.assertEqual(expected, list(a.Matches(comp)))

    comp = self._MakeComp([], 0, './o')
    print(list(a.Matches(comp)))

    # A bunch of repos in oilshell
    comp = self._MakeComp([], 0, '../o')
    print(list(a.Matches(comp)))

  def testShellFuncExecution(self):
    arena, c_parser = test_lib.InitCommandParser("""\
    f() {
      COMPREPLY=(f1 f2)
    }
    """)
    func_node = c_parser.ParseLogicalLine()
    print(func_node)

    ex = test_lib.InitExecutor(arena=arena)

    a = completion.ShellFuncAction(ex, func_node)
    comp = self._MakeComp(['f'], 0, 'f')
    matches = list(a.Matches(comp))
    self.assertEqual(['f1', 'f2'], matches)

  def testChainedCompleter(self):
    comp = self._MakeComp(['f'], 0, 'f')
    matches = list(C1.Matches(comp))
    self.assertEqual(['foo.py', 'foo'], matches)

    p = completion.GlobPredicate('*.py')
    c2 = completion.ChainedCompleter([A1], predicate=p)
    comp = self._MakeComp(['f'], 0, 'f')
    matches = list(c2.Matches(comp))
    self.assertEqual(['foo.py'], matches)

  def testRootCompleter(self):
    comp_lookup = completion.CompletionLookup()

    comp_lookup.RegisterName('grep', C1)
    comp_lookup.RegisterName('__first', FIRST)

    ev = test_lib.MakeTestEvaluator()

    pool = alloc.Pool()
    arena = pool.NewArena()
    parse_ctx = parse_lib.ParseContext(arena, {})
    var_comp = V1
    r = completion.RootCompleter(ev, comp_lookup, var_comp, parse_ctx,
                                 progress_f, debug_f)

    comp = completion.CompletionApi(line='grep f')
    m = list(r.Matches(comp))
    self.assertEqual(['foo.py', 'foo'], m)

    comp = completion.CompletionApi(line='grep g')
    m = list(r.Matches(comp))
    self.assertEqual([], m)

    m = list(r.Matches(completion.CompletionApi(line='ls $v')))
    self.assertEqual(['$var1', '$var2'], m)

    m = list(r.Matches(completion.CompletionApi(line='g')))
    self.assertEqual(['grep'], m)

    # Empty completer
    m = list(r.Matches(completion.CompletionApi('')))
    self.assertEqual(['grep', 'sed', 'test'], m)

    # Test compound commands. These PARSE
    m = list(r.Matches(completion.CompletionApi('echo hi || grep f')))
    m = list(r.Matches(completion.CompletionApi('echo hi; grep f')))

    # Brace -- does NOT parse
    m = list(r.Matches(completion.CompletionApi('{ echo hi; grep f')))
    # TODO: Test if/for/while/case/etc.

    m = list(r.Matches(completion.CompletionApi('var=$v')))
    m = list(r.Matches(completion.CompletionApi('local var=$v')))


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
