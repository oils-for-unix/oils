#!/usr/bin/env python
"""
process_test.py: Tests for process.py
"""

import os
import unittest

from core.id_kind import Id
from core import builtin
from osh import ast_ as ast

from core import process  # module under test
from core import runtime
from core import util
from core.cmd_exec_test import InitExecutor  # helper

Process = process.Process
ExternalThunk = process.ExternalThunk

log = util.log


def Banner(msg):
  print('-' * 60)
  print(msg)


_WAITER = process.Waiter()


def _ExtProc(argv):
  return Process(ExternalThunk(argv, {}))


class ProcessTest(unittest.TestCase):

  def testStdinRedirect(self):
    waiter = process.Waiter()
    fd_state = process.FdState()

    PATH = '_tmp/one-two.txt'
    # Write two lines
    with open(PATH, 'w') as f:
      f.write('one\ntwo\n')

    # Should get the first line twice, because Pop() closes it!

    r = runtime.PathRedirect(Id.Redir_Less, 0, PATH)
    fd_state.Push([r], waiter)
    line1 = builtin.ReadLineFromStdin()
    fd_state.Pop()

    fd_state.Push([r], waiter)
    line2 = builtin.ReadLineFromStdin()
    fd_state.Pop()

    # sys.stdin.readline() would erroneously return 'two' because of buffering.
    self.assertEqual('one\n', line1)
    self.assertEqual('one\n', line2)

  def testProcess(self):

    # 3 fds.  Does Python open it?  Shell seems to have it too.  Maybe it
    # inherits from the shell.
    print('FDS BEFORE', os.listdir('/dev/fd'))

    Banner('date')
    p = _ExtProc(['date'])
    status = p.Run(_WAITER)
    log('date returned %d', status)
    self.assertEqual(0, status)

    Banner('does-not-exist')
    p = _ExtProc(['does-not-exist'])
    print(p.Run(_WAITER))

    # 12 file descriptors open!
    print('FDS AFTER', os.listdir('/dev/fd'))

  def testPipeline(self):
    print('BEFORE', os.listdir('/dev/fd'))

    p = process.Pipeline()
    p.Add(_ExtProc(['ls']))
    p.Add(_ExtProc(['cut', '-d', '.', '-f', '2']))
    p.Add(_ExtProc(['sort']))
    p.Add(_ExtProc(['uniq', '-c']))

    pipe_status = p.Run(_WAITER)
    log('pipe_status: %s', pipe_status)

    print('AFTER', os.listdir('/dev/fd'))

  def testPipeline2(self):
    Banner('ls | cut -d . -f 1 | head')
    p = process.Pipeline()
    p.Add(_ExtProc(['ls']))
    p.Add(_ExtProc(['cut', '-d', '.', '-f', '1']))
    p.Add(_ExtProc(['head']))

    print(p.Run(_WAITER))

    ex = InitExecutor()

    # Simulating subshell for each command
    w1 = ast.CompoundWord()
    w1.parts.append(ast.LiteralPart(ast.token(Id.Lit_Chars, 'ls')))
    node1 = ast.SimpleCommand()
    node1.words = [w1]

    w2 = ast.CompoundWord()
    w2.parts.append(ast.LiteralPart(ast.token(Id.Lit_Chars, 'head')))
    node2 = ast.SimpleCommand()
    node2.words = [w2]

    w3 = ast.CompoundWord()
    w3.parts.append(ast.LiteralPart(ast.token(Id.Lit_Chars, 'sort')))
    w4 = ast.CompoundWord()
    w4.parts.append(ast.LiteralPart(ast.token(Id.Lit_Chars, '--reverse')))
    node3 = ast.SimpleCommand()
    node3.words = [w3, w4]

    p = process.Pipeline()
    p.Add(Process(process.SubProgramThunk(ex, node1)))
    p.Add(Process(process.SubProgramThunk(ex, node2)))
    p.Add(Process(process.SubProgramThunk(ex, node3)))

    print(p.Run(_WAITER))

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


if __name__ == '__main__':
  unittest.main()
