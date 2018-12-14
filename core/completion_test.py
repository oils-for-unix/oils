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


def MockApi(line):
  """Match readline's get_begidx() / get_endidx()."""
  end = len(line)
  i = end - 1
  while i > 0:
    if line[i] in util.READLINE_DELIMS:
      break
    i -= 1

  return completion.CompletionApi(line=line, begin=i+1, end=end)


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

    # TODO: This should set up the file system and $PATH and assert that only
    # executable files are accessed!

  def testFileSystemAction(self):
    a = completion.FileSystemAction()
    # Current dir -- all files and dirs
    comp = self._MakeComp([], 0, '')
    print(list(a.Matches(comp)))

    os.system('mkdir -p /tmp/oil_comp_test')
    os.system('bash -c "touch /tmp/oil_comp_test/{one,two,three}"')

    # TODO:
    # - This no longer filters by prefix!
    # - Should test that the executable bit works!

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

  def testRootCompleterCompletesVarNames(self):
    # Several cases here
    comp_lookup = completion.CompletionLookup()
    ev = test_lib.MakeTestEvaluator()

    pool = alloc.Pool()
    arena = pool.NewArena()
    parse_ctx = parse_lib.ParseContext(arena, {})
    r = completion.RootCompleter(ev, comp_lookup, mem, parse_ctx,
                                 progress_f, debug_f)

    # Complete ALL variables
    comp = MockApi('echo $')
    self.assertEqual(5, comp.begin)  # what readline does
    self.assertEqual(6, comp.end)
    print(comp)
    m = list(r.Matches(comp))
    # Just test for a subset
    self.assert_('$HOME' in m, m)
    self.assert_('$IFS' in m, m)

    # Now it has a prefix
    comp = MockApi(line='echo $P')
    self.assertEqual(5, comp.begin)  # what readline does
    self.assertEqual(7, comp.end)
    print(comp)
    m = list(r.Matches(comp))
    self.assert_('$PWD' in m, 'Got %s' % m)
    self.assert_('$PS4' in m, 'Got %s' % m)

    #
    # BracedVarSub
    #

    # Complete ALL variables
    comp = MockApi(line='echo ${')
    print(comp)
    m = list(r.Matches(comp))
    # Just test for a subset
    self.assert_('${HOME' in m, 'Got %s' % m)
    self.assert_('${IFS' in m, 'Got %s' % m)

    # Now it has a prefix
    comp = MockApi(line='echo ${P')
    print(comp)
    m = list(r.Matches(comp))
    self.assert_('${PWD' in m, 'Got %s' % m)
    self.assert_('${PS4' in m, 'Got %s' % m)

    # Odd word break
    # NOTE: We use VSub_Name both for $FOO and ${FOO.  Might be bad?
    comp = MockApi(line='echo ${undef:-$P')
    print(comp)
    m = list(r.Matches(comp))
    self.assert_('-$PWD' in m, 'Got %s' % m)
    self.assert_('-$PS4' in m, 'Got %s' % m)

    # Odd word break
    comp = MockApi(line='echo ${undef:-$')
    print(comp)
    m = list(r.Matches(comp))
    self.assert_('-$HOME' in m, 'Got %s' % m)
    self.assert_('-$IFS' in m, 'Got %s' % m)

    #
    # Double Quoted
    #
    # NOTE: GNU readline seems to complete closing quotes?  We don't want that.

    comp = MockApi(line='echo "$')
    print(comp)
    m = list(r.Matches(comp))
    self.assert_('$HOME' in m, 'Got %s' % m)  # don't need leading "
    self.assert_('$IFS' in m, 'Got %s' % m)

    comp = MockApi(line='echo "$P')
    print(comp)
    m = list(r.Matches(comp))
    self.assert_('$PWD' in m, 'Got %s' % m)  # don't need leading "
    self.assert_('$PS4' in m, 'Got %s' % m)

    #
    # Prefix operator
    #

    if 0:  # Here you need to handle VSub_Pound
      comp = MockApi(line='echo ${#')
      print(comp)
      m = list(r.Matches(comp))
      self.assert_('${#HOME' in m, 'Got %s' % m)
      self.assert_('${#IFS' in m, 'Got %s' % m)

    comp = MockApi(line='echo "${#P')
    print(comp)
    m = list(r.Matches(comp))
    self.assert_('${#PWD' in m, 'Got %s' % m)  # don't need leading "
    self.assert_('${#PS4' in m, 'Got %s' % m)

  def testRootCompleterCompletesOther(self):
    comp_lookup = completion.CompletionLookup()

    comp_lookup.RegisterName('grep', C1)
    comp_lookup.RegisterName('__first', FIRST)

    ev = test_lib.MakeTestEvaluator()

    pool = alloc.Pool()
    arena = pool.NewArena()
    parse_ctx = parse_lib.ParseContext(arena, {})
    r = completion.RootCompleter(ev, comp_lookup, mem, parse_ctx,
                                 progress_f, debug_f)

    comp = completion.CompletionApi(line='grep f')
    m = list(r.Matches(comp))
    self.assertEqual(['foo.py ', 'foo '], m)

    comp = completion.CompletionApi(line='grep g')
    m = list(r.Matches(comp))
    self.assertEqual([], m)

    m = list(r.Matches(completion.CompletionApi(line='g')))
    self.assertEqual(['grep '], m)

    # Empty completer
    m = list(r.Matches(MockApi('')))
    self.assertEqual(['grep ', 'sed ', 'test '], m)

    # Test compound commands. These PARSE
    m = list(r.Matches(completion.CompletionApi('echo hi || grep f')))
    m = list(r.Matches(completion.CompletionApi('echo hi; grep f')))

    # Brace -- does NOT parse
    m = list(r.Matches(completion.CompletionApi('{ echo hi; grep f')))
    # TODO: Test if/for/while/case/etc.

    m = list(r.Matches(completion.CompletionApi('var=$v')))
    m = list(r.Matches(completion.CompletionApi('local var=$v')))


def _TestCompKind(test, buf, check=True):
  """
  Args:
    check: Should we check it against the heuristic?
  """
  ev = test_lib.MakeTestEvaluator()
  arena = test_lib.MakeArena('<completion_test.py>')
  parse_ctx = parse_lib.ParseContext(arena, {})
  _, c_parser = parse_ctx.MakeParserForCompletion(buf, arena)
  print('--- %r' % buf)

  # TODO:
  # Create MockApi(buf) and pass it to RootCompleter


class PartialParseTest(unittest.TestCase):

  # Look at what kind of tree we get back
  def testLST(self):
    _TestCompKind(self, 'ls |', check=False)
    _TestCompKind(self, 'ls | ', check=False)

    _TestCompKind(self, 'ls ; ', check=False)
    _TestCompKind(self, 'ls && ', check=False)

    _TestCompKind(self, 'echo $(echo hi', check=False)
    # One word part
    _TestCompKind(self, 'echo a$(echo hi', check=False)
    _TestCompKind(self, 'echo a$x', check=False)

    # should we use a Lit_Dollar token here, for completion?
    _TestCompKind(self, 'echo $', check=False)
    _TestCompKind(self, 'echo $F', check=False)
    _TestCompKind(self, 'echo ${F', check=False)

    _TestCompKind(self, 'echo ${undef:-$', check=False)
    _TestCompKind(self, 'echo ${undef:-$F', check=False)

    # Complete var names in arith context??  Or funcs?
    _TestCompKind(self, 'echo $((', check=False)
    _TestCompKind(self, 'echo $(( ', check=False)
    # Lit_ArithVarLike could be completed.  The above 2 might not.
    # This could be a function too though, like f().
    _TestCompKind(self, 'echo $(( f', check=False)

  def testEmpty(self):
    _TestCompKind(self, '', check=False)
    _TestCompKind(self, ' ')

  def testCommands(self):
    # External
    _TestCompKind(self, 'ls')
    _TestCompKind(self, 'ls ')

    return
    # Redirect
    _TestCompKind(self, 'cat <')
    _TestCompKind(self, 'cat <input')

  def testCompound(self):
    return
    # Pipeline
    _TestCompKind(self, 'ls |', check=False)  # heuristic is WRONG
    _TestCompKind(self, 'ls | wc -l')

    # AndOr
    _TestCompKind(self, 'ls && ')
    _TestCompKind(self, 'ls && echo')

    # List
    _TestCompKind(self, 'echo a;')
    _TestCompKind(self, 'echo a; echo')

    # BraceGroup
    _TestCompKind(self, '{ echo hi;')
    _TestCompKind(self, '{ echo hi; echo')  # second word
    _TestCompKind(self, '{ echo hi; echo bye;')  # new command

    # Subshell
    _TestCompKind(self, '( echo hi')
    _TestCompKind(self, '( echo hi; echo')

    # FunctionDef
    _TestCompKind(self, 'f() {')
    _TestCompKind(self, 'f() { echo')
    _TestCompKind(self, 'f() { echo hi;')

    _TestCompKind(self, 'if')
    _TestCompKind(self, 'if ')
    _TestCompKind(self, 'if test ')

    _TestCompKind(self, 'while')
    _TestCompKind(self, 'while ')
    _TestCompKind(self, 'while test ')

    _TestCompKind(self, 'case $foo ')  # in
    _TestCompKind(self, 'case $foo in a)')
    _TestCompKind(self, 'case $foo in a) echo')

    # time construct
    _TestCompKind(self, 'time')
    _TestCompKind(self, 'time ')
    _TestCompKind(self, 'time echo')

  def testVarSub(self):
    return

    # TODO: Mem needs variable "f"

    # BracedVarSub
    _TestCompKind(self, 'echo $')
    _TestCompKind(self, 'echo $f')

    # Double Quoted BracedVarSub
    _TestCompKind(self, 'echo "$')
    _TestCompKind(self, 'echo "$f')

    # Braced var sub
    #print(f('echo ${'))  # TODO: FIx bug
    #print(f('echo ${f'))

    # Quoted Braced var sub
    #print(f('echo "${'))
    #print(f('echo "${f'))

    # Single quoted var sub should give nothing
    _TestCompKind(self, "echo '${")
    _TestCompKind(self, "echo '${f")

    # Array index
    #print(f('echo ${a['))
    #print(f('echo ${a[k'))

    # Var sub in command sub
    _TestCompKind(self, 'echo $(ls $')
    _TestCompKind(self, 'echo $(ls $f')

    # Var sub in var sub (bash doesn't do this)
    #print(f('echo ${a:-$'))
    #print(f('echo ${a:-$f'))

  def testCommandSub(self):
    return

    # CommandSubPart
    _TestCompKind(self, 'echo $(')
    _TestCompKind(self, 'echo $(ls ')
    _TestCompKind(self, 'echo $(ls foo')

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
