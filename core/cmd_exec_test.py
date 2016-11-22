#!/usr/bin/env python3
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
from core.tokens import Id
from core import ui
from core.word_node import LiteralPart, CommandWord, TestVarOp, VarSubPart
from core import word_eval
from core.value import Value
from core.cmd_node import SimpleCommandNode
from core.lexer import Token

from osh import parse_lib
from osh.word_parse import CommandWord, LiteralPart


def banner(msg):
  print('-' * 60)
  print(msg)


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
  return cmd_exec.Executor(mem, builtins, funcs, comp_funcs, exec_opts,
                           parse_lib.MakeParserForExecutor)


def InitEvaluator():
  mem = cmd_exec.Mem('', [])

  val1 = Value.FromString('xxx')
  val2 = Value.FromString('yyy')
  pairs = [('x', val1), ('y', val2)]
  mem.SetLocal(pairs, 0)

  exec_opts = cmd_exec.ExecOpts()
  # Don't need side effects for most things
  return word_eval.CompletionEvaluator(mem, exec_opts)


class ExecutorTest(unittest.TestCase):

  def testProcess(self):
    # 3 fds.  Does Python open it?  Shell seems to have it too.  Maybe it
    # inherits from the shell.
    print('FDS BEFORE', os.listdir('/dev/fd'))

    banner('date')
    p = Process(['date'])
    print(p.Run())

    banner('does-not-exist')
    p = Process(['does-not-exist'])
    print(p.Run())

    # 12 file descriptors open!
    print('FDS AFTER', os.listdir('/dev/fd'))

  def testPipeline(self):
    print('BEFORE', os.listdir('/dev/fd'))

    p = Pipeline()
    p.Add(Process(ExternalThunk(['ls'])))
    p.Add(Process(ExternalThunk(['cut', '-d', '.', '-f', '2'])))
    p.Add(Process(ExternalThunk(['sort'])))
    p.Add(Process(ExternalThunk(['uniq', '-c'])))

    p.Run()

    print('AFTER', os.listdir('/dev/fd'))

  def testPipeline2(self):
    banner('ls | cut -d . -f 1 | head')
    p = Pipeline()
    p.Add(Process(ExternalThunk(['ls'])))
    p.Add(Process(ExternalThunk(['cut', '-d', '.', '-f', '1'])))
    p.Add(Process(ExternalThunk(['head'])))

    print(p.Run())

    ex = InitExecutor()

    # Simulating subshell for each command
    w1 = CommandWord()
    w1.parts.append(LiteralPart(Token(Id.Lit_Chars, 'ls')))
    node1 = SimpleCommandNode()
    node1.words = [w1]

    w2 = CommandWord()
    w2.parts.append(LiteralPart(Token(Id.Lit_Chars, 'head')))
    node2 = SimpleCommandNode()
    node2.words = [w2]

    w3 = CommandWord()
    w3.parts.append(LiteralPart(Token(Id.Lit_Chars, 'sort')))
    w4 = CommandWord()
    w4.parts.append(LiteralPart(Token(Id.Lit_Chars, '--reverse')))
    node3 = SimpleCommandNode()
    node3.words = [w3, w4]

    p = Pipeline()
    p.Add(Process(SubProgramThunk(ex, node1)))
    p.Add(Process(SubProgramThunk(ex, node2)))
    p.Add(Process(SubProgramThunk(ex, node3)))

    print(p.Run())

    # TODO: Combine pipelines for other things:

    # echo foo 1>&2 | tee stdout.txt
    #
    # foo=$(ls | head)
    #
    # foo=$(<<EOF ls | head)
    # stdin
    # EOF
    #
    # ls | head &

    # Or technically we could fork the whole interpreter for foo|bar|baz and
    # capture stdout of that interpreter.


class RedirectTest(unittest.TestCase):

  def testHereRedirects(self):
    # NOTE: THis starts another process, which confuses unit test framework!
    return
    fd_state = FdState()
    r = HereDocRedirect(Id.Redir_DLess, 0, 'hello\n')
    r.ApplyInParent(fd_state)

    in_str = sys.stdin.readline()
    print(repr(in_str))

    fd_state.RestoreAll()

  def testFilenameRedirect(self):
    print('BEFORE', os.listdir('/dev/fd'))

    fd_state = FdState()
    r = DescriptorRedirect(Id.Redir_GreatAnd, 1, 2)  # 1>&2
    r.ApplyInParent(fd_state)

    sys.stdout.write('write stdout to stderr\n')
    #os.write(sys.stdout.fileno(), 'write stdout to stderr\n')
    sys.stdout.flush()  # flush required

    fd_state.RestoreAll()

    sys.stdout.write('after restoring stdout\n')
    sys.stdout.flush()  # flush required

    r1 = FilenameRedirect(Id.Redir_Great, 1, '_tmp/desc3-out.txt')
    r2 = FilenameRedirect(Id.Redir_Great, 2, '_tmp/desc3-err.txt')

    r1.ApplyInParent(fd_state)
    r2.ApplyInParent(fd_state)

    sys.stdout.write('stdout to file\n')
    sys.stdout.flush()  # flush required
    sys.stderr.write('stderr to file\n')
    sys.stderr.flush()  # flush required

    fd_state.RestoreAll()

    r1 = FilenameRedirect(Id.Redir_Great, 1, '_tmp/ls-out.txt')
    r2 = FilenameRedirect(Id.Redir_Great, 2, '_tmp/ls-err.txt')

    p = Process(
        ExternalThunk(['ls', '/error', '.']), fd_state=fd_state,
        redirects=[r1, r2])

    print(p.Run())

    return

    # Bad File Descriptor
    ok = fd_state.SaveAndDup(5, 1)  # 1>&5

    if ok:
      sys.stdout.write('write stdout to stderr\n')
      sys.stdout.flush()  # flush required
      fd_state.RestoreAll()
    else:
      print('SaveAndDup FAILED')

    print('FDs AFTER', os.listdir('/dev/fd'))


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
    print(node.DebugString())
    print(node.words)

    ex = InitExecutor()
    #print(ex.Execute(node))

    #print(ex._ExpandWords(node.words))


class VarOpTest(unittest.TestCase):

  def testVarOps(self):
    ev = InitEvaluator()  # initializes x=xxx and y=yyy
    unset_sub = VarSubPart('unset')
    print(ev.EvalVarSub(unset_sub))

    set_sub = VarSubPart('x')
    print(ev.EvalVarSub(set_sub))

    part = LiteralPart(Token(Id.Lit_Chars, 'default'))
    arg_word = CommandWord(parts=[part])
    test_op = TestVarOp(Id.VTest_ColonHyphen, arg_word)
    unset_sub.test_op = test_op
    set_sub.test_op = test_op

    print(ev.EvalVarSub(unset_sub))
    print(ev.EvalVarSub(set_sub))


if __name__ == '__main__':
  unittest.main()
