#!/usr/bin/env python2
"""
process_test.py: Tests for process.py
"""

import os
import unittest

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import (
    redirect, redirect_arg, cmd_value, trace
)
from _devbuild.gen.syntax_asdl import redir_loc
from asdl import runtime
from core import dev
from core import process  # module under test
from core import pyos
from core import test_lib
from core import ui
from core import util
from core.pyerror import log
from core import state
from osh import builtin_misc, builtin_trap
from mycpp import mylib

Process = process.Process
ExternalThunk = process.ExternalThunk


def Banner(msg):
  print('-' * 60)
  print(msg)


def _CommandNode(code_str, arena):
  c_parser = test_lib.InitCommandParser(code_str, arena=arena)
  return c_parser.ParseLogicalLine()


class ProcessTest(unittest.TestCase):

  def setUp(self):
    self.arena = test_lib.MakeArena('process_test.py')

    mem = state.Mem('', [], self.arena, [])
    parse_opts, exec_opts, mutable_opts = state.MakeOpts(mem, None)
    mem.exec_opts = exec_opts

    state.InitMem(mem, {}, '0.1')

    self.job_state = process.JobState()
    trap_state = builtin_trap.TrapState()
    self.tracer = dev.Tracer(None, exec_opts, mutable_opts, mem, mylib.Stderr())
    self.waiter = process.Waiter(self.job_state, exec_opts, trap_state, self.tracer)
    errfmt = ui.ErrorFormatter(self.arena)
    self.fd_state = process.FdState(errfmt, self.job_state, None, self.tracer, None)
    self.ext_prog = process.ExternalProgram('', self.fd_state, errfmt,
                                            util.NullDebugFile())

  def _ExtProc(self, argv):
    arg_vec = cmd_value.Argv(argv, [0] * len(argv))
    argv0_path = None
    for path_entry in ['/bin', '/usr/bin']:
      full_path = os.path.join(path_entry, argv[0])
      if os.path.exists(full_path):
        argv0_path = full_path
        break
    if not argv0_path:
      argv0_path = argv[0]  # fallback that tests failure case
    return Process(ExternalThunk(self.ext_prog, argv0_path, arg_vec, {}),
                   self.job_state, self.tracer)

  def testStdinRedirect(self):
    PATH = '_tmp/one-two.txt'
    # Write two lines
    with open(PATH, 'w') as f:
      f.write('one\ntwo\n')

    # Should get the first line twice, because Pop() closes it!

    r = redirect(Id.Redir_Less, runtime.NO_SPID, redir_loc.Fd(0),
                 redirect_arg.Path(PATH))

    class CommandEvaluator(object):
      def RunPendingTraps(self):
        pass
    cmd_ev = CommandEvaluator()

    self.fd_state.Push([r])
    line1, _ = builtin_misc._ReadUntilDelim(pyos.NEWLINE_CH, cmd_ev)
    self.fd_state.Pop()

    self.fd_state.Push([r])
    line2, _ = builtin_misc._ReadUntilDelim(pyos.NEWLINE_CH, cmd_ev)
    self.fd_state.Pop()

    # sys.stdin.readline() would erroneously return 'two' because of buffering.
    self.assertEqual('one', line1)
    self.assertEqual('one', line2)

  def testProcess(self):

    # 3 fds.  Does Python open it?  Shell seems to have it too.  Maybe it
    # inherits from the shell.
    print('FDS BEFORE', os.listdir('/dev/fd'))

    Banner('date')
    argv = ['date']
    p = self._ExtProc(argv)
    why = trace.External(argv)
    status = p.RunWait(self.waiter, why)
    log('date returned %d', status)
    self.assertEqual(0, status)

    Banner('does-not-exist')
    p = self._ExtProc(['does-not-exist'])
    print(p.RunWait(self.waiter, why))

    # 12 file descriptors open!
    print('FDS AFTER', os.listdir('/dev/fd'))

  def testPipeline(self):
    node = _CommandNode('uniq -c', self.arena)
    cmd_ev = test_lib.InitCommandEvaluator(arena=self.arena, ext_prog=self.ext_prog)
    print('BEFORE', os.listdir('/dev/fd'))

    p = process.Pipeline(False)
    p.Add(self._ExtProc(['ls']))
    p.Add(self._ExtProc(['cut', '-d', '.', '-f', '2']))
    p.Add(self._ExtProc(['sort']))

    p.AddLast((cmd_ev, node))

    pipe_status = p.Run(self.waiter, self.fd_state)
    log('pipe_status: %s', pipe_status)

    print('AFTER', os.listdir('/dev/fd'))

  def testPipeline2(self):
    cmd_ev = test_lib.InitCommandEvaluator(arena=self.arena, ext_prog=self.ext_prog)

    Banner('ls | cut -d . -f 1 | head')
    p = process.Pipeline(False)
    p.Add(self._ExtProc(['ls']))
    p.Add(self._ExtProc(['cut', '-d', '.', '-f', '1']))

    node = _CommandNode('head', self.arena)
    p.AddLast((cmd_ev, node))

    print(p.Run(self.waiter, self.fd_state))

    # Simulating subshell for each command
    node1 = _CommandNode('ls', self.arena)
    node2 = _CommandNode('head', self.arena)
    node3 = _CommandNode('sort --reverse', self.arena)

    p = process.Pipeline(False)
    p.Add(Process(process.SubProgramThunk(cmd_ev, node1), self.job_state, self.tracer)) 
    p.Add(Process(process.SubProgramThunk(cmd_ev, node2), self.job_state, self.tracer))
    p.Add(Process(process.SubProgramThunk(cmd_ev, node3), self.job_state, self.tracer))

    last_thunk = (cmd_ev, _CommandNode('cat', self.arena))
    p.AddLast(last_thunk)

    print(p.Run(self.waiter, self.fd_state))

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

  def testOpen(self):
    # Disabled because mycpp translation can't handle it.  We do this at a
    # higher layer.
    return

    # This function used to raise BOTH OSError and IOError because Python 2 is
    # inconsistent.
    # We follow Python 3 in preferring OSError.
    # https://stackoverflow.com/questions/29347790/difference-between-ioerror-and-oserror
    self.assertRaises(OSError, self.fd_state.Open, '_nonexistent_')
    self.assertRaises(OSError, self.fd_state.Open, 'metrics/')


if __name__ == '__main__':
  unittest.main()
