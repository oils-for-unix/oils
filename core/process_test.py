#!/usr/bin/env python2
"""
process_test.py: Tests for process.py
"""

import os
import unittest

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.option_asdl import option_i
from _devbuild.gen.runtime_asdl import (
    redirect, redirect_arg, cmd_value
)
from _devbuild.gen.syntax_asdl import redir_loc
from core import optview
from core import process  # module under test
from core import test_lib
from core import ui
from core import util
from core.util import log
from core import state
from osh import builtin_misc
from asdl import runtime

Process = process.Process
ExternalThunk = process.ExternalThunk


def Banner(msg):
  print('-' * 60)
  print(msg)


# TODO: Put these all in a function.
_ARENA = test_lib.MakeArena('process_test.py')

_MEM = state.Mem('', [], _ARENA, [])
state.InitMem(_MEM, {}, '0.1')

_OPT_ARRAY = [False] * option_i.ARRAY_SIZE
_PARSE_OPTS = optview.Parse(_OPT_ARRAY)
_ERREXIT = state._ErrExit()
_EXEC_OPTS = state.MutableOpts(_MEM, _OPT_ARRAY, _ERREXIT, None)
_JOB_STATE = process.JobState()
_WAITER = process.Waiter(_JOB_STATE, _EXEC_OPTS)
_ERRFMT = ui.ErrorFormatter(_ARENA)
_FD_STATE = process.FdState(_ERRFMT, _JOB_STATE)
_EXT_PROG = process.ExternalProgram(False, _FD_STATE, _ERRFMT,
                                    util.NullDebugFile())


def _CommandNode(code_str, arena):
  c_parser = test_lib.InitCommandParser(code_str, arena=arena)
  return c_parser.ParseLogicalLine()


def _ExtProc(argv):
  arg_vec = cmd_value.Argv(argv, [0] * len(argv))
  argv0_path = None
  for path_entry in ['/bin', '/usr/bin']:
    full_path = os.path.join(path_entry, argv[0])
    if os.path.exists(full_path):
      argv0_path = full_path
      break
  if not argv0_path:
    argv0_path = argv[0]  # fallback that tests failure case
  return Process(ExternalThunk(_EXT_PROG, argv0_path, arg_vec, {}), _JOB_STATE)


class ProcessTest(unittest.TestCase):

  def testStdinRedirect(self):
    waiter = process.Waiter(_JOB_STATE, _EXEC_OPTS)
    fd_state = process.FdState(_ERRFMT, _JOB_STATE)

    PATH = '_tmp/one-two.txt'
    # Write two lines
    with open(PATH, 'w') as f:
      f.write('one\ntwo\n')

    # Should get the first line twice, because Pop() closes it!

    r = redirect(Id.Redir_Less, runtime.NO_SPID, redir_loc.Fd(0),
                 redirect_arg.Path(PATH))

    fd_state.Push([r], waiter)
    line1, _ = builtin_misc.ReadLineFromStdin('\n')
    fd_state.Pop()

    fd_state.Push([r], waiter)
    line2, _ = builtin_misc.ReadLineFromStdin('\n')
    fd_state.Pop()

    # sys.stdin.readline() would erroneously return 'two' because of buffering.
    self.assertEqual('one', line1)
    self.assertEqual('one', line2)

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
    node = _CommandNode('uniq -c', _ARENA)
    cmd_ev = test_lib.InitCommandEvaluator(arena=_ARENA, ext_prog=_EXT_PROG)
    print('BEFORE', os.listdir('/dev/fd'))

    p = process.Pipeline()
    p.Add(_ExtProc(['ls']))
    p.Add(_ExtProc(['cut', '-d', '.', '-f', '2']))
    p.Add(_ExtProc(['sort']))

    p.AddLast((cmd_ev, node))

    pipe_status = p.Run(_WAITER, _FD_STATE)
    log('pipe_status: %s', pipe_status)

    print('AFTER', os.listdir('/dev/fd'))

  def testPipeline2(self):
    cmd_ev = test_lib.InitCommandEvaluator(arena=_ARENA, ext_prog=_EXT_PROG)

    Banner('ls | cut -d . -f 1 | head')
    p = process.Pipeline()
    p.Add(_ExtProc(['ls']))
    p.Add(_ExtProc(['cut', '-d', '.', '-f', '1']))

    node = _CommandNode('head', _ARENA)
    p.AddLast((cmd_ev, node))

    fd_state = process.FdState(_ERRFMT, _JOB_STATE)
    print(p.Run(_WAITER, _FD_STATE))

    # Simulating subshell for each command
    node1 = _CommandNode('ls', _ARENA)
    node2 = _CommandNode('head', _ARENA)
    node3 = _CommandNode('sort --reverse', _ARENA)

    p = process.Pipeline()
    p.Add(Process(process.SubProgramThunk(cmd_ev, node1), _JOB_STATE))
    p.Add(Process(process.SubProgramThunk(cmd_ev, node2), _JOB_STATE))
    p.Add(Process(process.SubProgramThunk(cmd_ev, node3), _JOB_STATE))

    last_thunk = (cmd_ev, _CommandNode('cat', _ARENA))
    p.AddLast(last_thunk)

    print(p.Run(_WAITER, _FD_STATE))

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
    fd_state = process.FdState(_ERRFMT, _JOB_STATE)

    # This function used to raise BOTH OSError and IOError because Python 2 is
    # inconsistent.
    # We follow Python 3 in preferring OSError.
    # https://stackoverflow.com/questions/29347790/difference-between-ioerror-and-oserror
    self.assertRaises(OSError, fd_state.Open, '_nonexistent_')
    self.assertRaises(OSError, fd_state.Open, 'metrics/')


if __name__ == '__main__':
  unittest.main()
