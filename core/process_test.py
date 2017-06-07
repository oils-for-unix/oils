#!/usr/bin/python -S
"""
process_test.py: Tests for process.py
"""

import os
import sys
import unittest

from core.id_kind import Id
from osh import ast_ as ast

from core import process  # module under test
from core import util
from core.cmd_exec_test import InitExecutor  # helper

Process = process.Process
ExternalThunk = process.ExternalThunk

log = util.log


def Banner(msg):
  print('-' * 60)
  print(msg)


_WAITER = process.Waiter()


class ProcessTest(unittest.TestCase):

  def testProcess(self):

    # 3 fds.  Does Python open it?  Shell seems to have it too.  Maybe it
    # inherits from the shell.
    print('FDS BEFORE', os.listdir('/dev/fd'))

    Banner('date')
    p = Process(ExternalThunk(['date']))
    status = p.Run(_WAITER)
    log('date returned %d', status)
    self.assertEqual(0, status)

    Banner('does-not-exist')
    p = Process(ExternalThunk(['does-not-exist']))
    print(p.Run(_WAITER))

    # 12 file descriptors open!
    print('FDS AFTER', os.listdir('/dev/fd'))

  def testPipeline(self):
    print('BEFORE', os.listdir('/dev/fd'))

    p = process.Pipeline()
    p.Add(Process(ExternalThunk(['ls'])))
    p.Add(Process(ExternalThunk(['cut', '-d', '.', '-f', '2'])))
    p.Add(Process(ExternalThunk(['sort'])))
    p.Add(Process(ExternalThunk(['uniq', '-c'])))

    pipe_status = p.Run(_WAITER)
    log('pipe_status: %s', pipe_status)

    print('AFTER', os.listdir('/dev/fd'))

  def testPipeline2(self):
    Banner('ls | cut -d . -f 1 | head')
    p = process.Pipeline()
    p.Add(Process(ExternalThunk(['ls'])))
    p.Add(Process(ExternalThunk(['cut', '-d', '.', '-f', '1'])))
    p.Add(Process(ExternalThunk(['head'])))

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


class RedirectTest(unittest.TestCase):

  def testHereRedirects(self):
    # NOTE: THis starts another process, which confuses unit test framework!
    return
    fd_state = process.FdState()
    r = HereDocRedirect(Id.Redir_DLess, 0, 'hello\n')
    r.ApplyInParent(fd_state)

    in_str = sys.stdin.readline()
    print(repr(in_str))

    fd_state.PopAndRestore()

  def testFilenameRedirect(self):
    print('BEFORE', os.listdir('/dev/fd'))

    fd_state = process.FdState()
    r = process.DescriptorRedirect(Id.Redir_GreatAnd, 1, 2)  # 1>&2
    r.ApplyInParent(fd_state)

    sys.stdout.write('write stdout to stderr\n')
    #os.write(sys.stdout.fileno(), 'write stdout to stderr\n')
    sys.stdout.flush()  # flush required

    fd_state.PopAndRestore()

    fd_state.PushFrame()

    sys.stdout.write('after restoring stdout\n')
    sys.stdout.flush()  # flush required

    r1 = process.FilenameRedirect(Id.Redir_Great, 1, '_tmp/desc3-out.txt')
    r2 = process.FilenameRedirect(Id.Redir_Great, 2, '_tmp/desc3-err.txt')

    r1.ApplyInParent(fd_state)
    r2.ApplyInParent(fd_state)

    sys.stdout.write('stdout to file\n')
    sys.stdout.flush()  # flush required
    sys.stderr.write('stderr to file\n')
    sys.stderr.flush()  # flush required

    fd_state.PopAndRestore()

    r1 = process.FilenameRedirect(Id.Redir_Great, 1, '_tmp/ls-out.txt')
    r2 = process.FilenameRedirect(Id.Redir_Great, 2, '_tmp/ls-err.txt')

    p = Process(
        process.ExternalThunk(['ls', '/error', '.']), fd_state=fd_state,
        redirects=[r1, r2])

    # Bad File Descriptor
    ok = fd_state.SaveAndDup(5, 1)  # 1>&5

    if ok:
      sys.stdout.write('write stdout to stderr\n')
      sys.stdout.flush()  # flush required
      fd_state.PopAndRestore()
    else:
      print('SaveAndDup FAILED')

    print('FDs AFTER', os.listdir('/dev/fd'))


if __name__ == '__main__':
  unittest.main()
