#!/usr/bin/env python2
"""process_test.py: Tests for process.py."""

import os
import unittest

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import (RedirValue, redirect_arg, cmd_value,
                                        trace)
from _devbuild.gen.syntax_asdl import loc, redir_loc
from asdl import runtime
from builtin import read_osh
from builtin import process_osh
from builtin import trap_osh
from core import dev
from core import process  # module under test
from core import pyos
from core import sh_init
from core import state
from core import test_lib
from core import util
from display import ui
from frontend import flag_def  # side effect: flags are defined, for wait builtin
from mycpp import iolib
from mycpp import mylib
from mycpp.mylib import log

import posix_ as posix

_ = flag_def

Process = process.Process
ExternalThunk = process.ExternalThunk


def Banner(msg):
    print('-' * 60)
    print(msg)


class _FakeJobControl(object):

    def __init__(self, enabled):
        self.enabled = enabled

    def Enabled(self):
        return self.enabled


class _FakeCommandEvaluator(object):

    def RunPendingTraps(self):
        pass


def _SetupTest(self):
    self.arena = test_lib.MakeArena('process_test.py')

    self.mem = test_lib.MakeMem(self.arena)
    parse_opts, exec_opts, mutable_opts = state.MakeOpts(self.mem, {}, None)
    self.mem.exec_opts = exec_opts

    #state.InitMem(mem, {}, '0.1')
    sh_init.InitDefaultVars(self.mem, [])

    self.job_control = process.JobControl()
    self.job_list = process.JobList()

    signal_safe = iolib.InitSignalSafe()
    self.trap_state = trap_osh.TrapState(signal_safe)

    fd_state = None
    self.multi_trace = dev.MultiTracer(posix.getpid(), '', '', '', fd_state)
    self.tracer = dev.Tracer(None, exec_opts, mutable_opts, self.mem,
                             mylib.Stderr(), self.multi_trace)
    self.waiter = process.Waiter(self.job_list, exec_opts, self.trap_state,
                                 self.tracer)
    self.errfmt = ui.ErrorFormatter()
    self.fd_state = process.FdState(self.errfmt, self.job_control,
                                    self.job_list, None, self.tracer, None,
                                    exec_opts)
    self.ext_prog = process.ExternalProgram('', self.fd_state, self.errfmt,
                                            util.NullDebugFile())
    self.cmd_ev = test_lib.InitCommandEvaluator(arena=self.arena,
                                                ext_prog=self.ext_prog)


def _MakeThunk(argv, ext_prog):
    arg_vec = cmd_value.Argv(argv, [loc.Missing] * len(argv), False, None,
                             None)
    argv0_path = None
    for path_entry in ['/bin', '/usr/bin']:
        full_path = os.path.join(path_entry, argv[0])
        if os.path.exists(full_path):
            argv0_path = full_path
            break
    if not argv0_path:
        argv0_path = argv[0]  # fallback that tests failure case
    return ExternalThunk(ext_prog, argv0_path, arg_vec, {})


def _CommandNode(code_str, arena):
    c_parser = test_lib.InitCommandParser(code_str, arena=arena)
    return c_parser.ParseLogicalLine()


class _Common(unittest.TestCase):
    """Common functionality for tests below."""

    def setUp(self):
        _SetupTest(self)

    def _ExtProc(self, argv):
        thunk = _MakeThunk(argv, self.ext_prog)
        return Process(thunk, self.job_control, self.job_list, self.tracer)

    def _MakePipeline(self, argv_list, last_str=''):
        assert len(last_str), last_str  # required

        pi = process.Pipeline(False, self.job_control, self.job_list,
                              self.tracer)
        for argv in argv_list:
            pi.Add(self._ExtProc(argv))
        node = _CommandNode(last_str, self.arena)
        pi.AddLast((self.cmd_ev, node))
        return pi


class ProcessTest(_Common):

    def testStdinRedirect(self):
        PATH = '_tmp/one-two.txt'
        # Write two lines
        with open(PATH, 'w') as f:
            f.write('one\ntwo\n')

        # Should get the first line twice, because Pop() closes it!

        r = RedirValue(Id.Redir_Less, runtime.NO_SPID, redir_loc.Fd(0),
                       redirect_arg.Path(PATH))

        cmd_ev = _FakeCommandEvaluator()

        err_out = []
        self.fd_state.Push([r], err_out)
        line1, _ = read_osh._ReadPortion(pyos.NEWLINE_CH, -1, cmd_ev)
        self.fd_state.Pop(err_out)

        self.fd_state.Push([r], err_out)
        line2, _ = read_osh._ReadPortion(pyos.NEWLINE_CH, -1, cmd_ev)
        self.fd_state.Pop(err_out)

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
        status = p.RunProcess(self.waiter, why)
        log('date returned %d', status)
        self.assertEqual(0, status)

        Banner('does-not-exist')
        p = self._ExtProc(['does-not-exist'])
        print(p.RunProcess(self.waiter, why))

        # 12 file descriptors open!
        print('FDS AFTER', os.listdir('/dev/fd'))

    def testPipeline(self):
        print('BEFORE', os.listdir('/dev/fd'))

        p = self._MakePipeline(
            [['ls'], ['cut', '-d', '.', '-f', '2'], ['sort']],
            last_str='uniq -c')

        p.StartPipeline(self.waiter)
        pipe_status = p.RunLastPart(self.waiter, self.fd_state)
        log('pipe_status: %s', pipe_status)

        print('AFTER', os.listdir('/dev/fd'))

    def testPipeline2(self):
        Banner('ls | cut -d . -f 1 | head')
        p = self._MakePipeline([['ls'], ['cut', '-d', '.', '-f', '1']],
                               last_str='head')

        p.StartPipeline(self.waiter)
        print(p.RunLastPart(self.waiter, self.fd_state))

    def testPipeline3(self):
        # Simulating subshell for each command
        node1 = _CommandNode('ls', self.arena)
        node2 = _CommandNode('head', self.arena)
        node3 = _CommandNode('sort --reverse', self.arena)

        thunk1 = process.SubProgramThunk(self.cmd_ev, node1, self.trap_state,
                                         self.multi_trace, True, False)
        thunk2 = process.SubProgramThunk(self.cmd_ev, node2, self.trap_state,
                                         self.multi_trace, True, False)
        thunk3 = process.SubProgramThunk(self.cmd_ev, node3, self.trap_state,
                                         self.multi_trace, True, False)

        p = process.Pipeline(False, self.job_control, self.job_list,
                             self.tracer)
        p.Add(Process(thunk1, self.job_control, self.job_list, self.tracer))
        p.Add(Process(thunk2, self.job_control, self.job_list, self.tracer))
        p.Add(Process(thunk3, self.job_control, self.job_list, self.tracer))

        last_thunk = (self.cmd_ev, _CommandNode('cat', self.arena))
        p.AddLast(last_thunk)

        p.StartPipeline(self.waiter)
        print(p.RunLastPart(self.waiter, self.fd_state))

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

    def _MakePipeline2(self, jc):
        pi = process.Pipeline(False, jc, self.job_list, self.tracer)

        node1 = _CommandNode('/bin/echo testpipeline', self.arena)
        node2 = _CommandNode('cat', self.arena)

        thunk1 = process.SubProgramThunk(self.cmd_ev, node1, self.trap_state,
                                         self.multi_trace, True, False)
        thunk2 = process.SubProgramThunk(self.cmd_ev, node2, self.trap_state,
                                         self.multi_trace, True, False)

        pi.Add(Process(thunk1, jc, self.job_list, self.tracer))
        pi.Add(Process(thunk2, jc, self.job_list, self.tracer))

        return pi

    def testPipelinePgidField(self):
        jc = _FakeJobControl(False)

        pi = self._MakePipeline2(jc)
        self.assertEqual(process.INVALID_PGID, pi.ProcessGroupId())

        pi.StartPipeline(self.waiter)
        # No pgid
        self.assertEqual(process.INVALID_PGID, pi.ProcessGroupId())

        jc = _FakeJobControl(True)

        pi = self._MakePipeline2(jc)
        self.assertEqual(process.INVALID_PGID, pi.ProcessGroupId())

        pi.StartPipeline(self.waiter)
        # first process is the process group leader
        self.assertEqual(pi.pids[0], pi.ProcessGroupId())

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


class JobListTest(_Common):
    """
    Test invariant that the 'wait' builtin removes the (pid -> status)
    mappings (NOT the Waiter)

    There are 4 styles of invoking it:

    wait              # for all
    wait -n           # for next
    wait $pid1 $pid2  # for specific jobs -- problem: are pipelines included?
    wait %j1   %j2    # job specs -- jobs are either pielines or processes

    Bonus:

    jobs -l can show exit status
    """

    def setUp(self):
        _SetupTest(self)

        self.wait_builtin = process_osh.Wait(self.waiter, self.job_list,
                                             self.mem, self.tracer,
                                             self.errfmt)

    def _RunBackgroundJob(self, argv):
        p = self._ExtProc(argv)

        # Similar to Executor::RunBackgroundJob()
        p.SetBackground()
        pid = p.StartProcess(trace.Fork)

        #self.mem.last_bg_pid = pid  # for $!

        job_id = self.job_list.RegisterJob(p)  # show in 'jobs' list
        return pid, job_id

    def _StartProcesses(self, n):
        pids = []
        job_ids = []

        assert n < 10, n
        for i in xrange(1, n + 1):
            j = 10 - i  # count down
            argv = ['sh', '-c', 'sleep 0.0%d; echo i=%d; exit %d' % (j, j, j)]
            pid, job_id = self._RunBackgroundJob(argv)
            pids.append(pid)
            job_ids.append(job_id)

        log('pids %s', pids)
        log('job_ids %s', job_ids)

        return pids, job_ids

    def assertJobListLength(self, length):
        self.assertEqual(length, len(self.job_list.child_procs))
        self.assertEqual(length, len(self.job_list.jobs))
        self.assertEqual(length, len(self.job_list.pid_to_job))

    def testWaitAll(self):
        """ wait """
        # Jobs list starts out empty
        self.assertJobListLength(0)

        # Fork 2 processes with &
        pids, job_ids = self._StartProcesses(2)

        # Now we have 2 jobs
        self.assertJobListLength(2)

        # Invoke the 'wait' builtin

        cmd_val = test_lib.MakeBuiltinArgv(['wait'])
        status = self.wait_builtin.Run(cmd_val)
        self.assertEqual(0, status)

        # Jobs list is now empty
        self.assertJobListLength(0)

    def testWaitNext(self):
        """ wait -n """
        # Jobs list starts out empty
        self.assertJobListLength(0)

        # Fork 2 processes with &
        pids, job_ids = self._StartProcesses(2)

        # Now we have 2 jobs
        self.assertJobListLength(2)

        ### 'wait -n'
        cmd_val = test_lib.MakeBuiltinArgv(['wait', '-n'])
        status = self.wait_builtin.Run(cmd_val)
        self.assertEqual(8, status)

        # Jobs list now has 1 fewer job
        self.assertJobListLength(1)

        ### 'wait -n' again
        cmd_val = test_lib.MakeBuiltinArgv(['wait', '-n'])
        status = self.wait_builtin.Run(cmd_val)
        self.assertEqual(9, status)

        # Now zero
        self.assertJobListLength(0)

        ### 'wait -n' again
        cmd_val = test_lib.MakeBuiltinArgv(['wait', '-n'])
        status = self.wait_builtin.Run(cmd_val)
        self.assertEqual(127, status)

        # Still zero
        self.assertJobListLength(0)

    def testWaitPid(self):
        """ wait $pid2 """
        # Jobs list starts out empty
        self.assertJobListLength(0)

        # Fork 3 processes with &
        pids, job_ids = self._StartProcesses(3)

        # Now we have 3 jobs
        self.assertJobListLength(3)

        # wait $pid2
        cmd_val = test_lib.MakeBuiltinArgv(['wait', str(pids[1])])
        status = self.wait_builtin.Run(cmd_val)
        self.assertEqual(8, status)

        # Jobs list now has 1 fewer job
        self.assertJobListLength(2)

        # wait $pid3
        cmd_val = test_lib.MakeBuiltinArgv(['wait', str(pids[2])])
        status = self.wait_builtin.Run(cmd_val)
        self.assertEqual(7, status)

        self.assertJobListLength(1)

        # wait $pid1
        cmd_val = test_lib.MakeBuiltinArgv(['wait', str(pids[0])])
        status = self.wait_builtin.Run(cmd_val)
        self.assertEqual(9, status)

        self.assertJobListLength(0)

    def testWaitJob(self):
        """ wait %j2 """

        # Jobs list starts out empty
        self.assertJobListLength(0)

        # Fork 3 processes with &
        pids, job_ids = self._StartProcesses(3)

        # Now we have 3 jobs
        self.assertJobListLength(3)

        # wait %j2
        cmd_val = test_lib.MakeBuiltinArgv(['wait', '%' + str(job_ids[1])])
        status = self.wait_builtin.Run(cmd_val)
        self.assertEqual(8, status)

        self.assertJobListLength(2)

        # wait %j3
        cmd_val = test_lib.MakeBuiltinArgv(['wait', '%' + str(job_ids[2])])

        status = self.wait_builtin.Run(cmd_val)
        self.assertEqual(7, status)

        self.assertJobListLength(1)

        # wait %j1
        cmd_val = test_lib.MakeBuiltinArgv(['wait', '%' + str(job_ids[0])])
        status = self.wait_builtin.Run(cmd_val)
        self.assertEqual(9, status)

        self.assertJobListLength(0)

    def testForegroundProcessCleansUpChildProcessDict(self):
        self.assertJobListLength(0)

        argv = ['sleep', '0.01']
        p = self._ExtProc(argv)
        why = trace.External(argv)
        p.RunProcess(self.waiter, why)

        self.assertJobListLength(0)

    def testGrandchildOutlivesChild(self):
        """ The new parent is the init process """

        # Jobs list starts out empty
        self.assertEqual(0, len(self.job_list.child_procs))

        # the sleep process should outlive the sh process
        argv = ['sh', '-c', 'sleep 0.1 & exit 99']
        pid, job_id = self._RunBackgroundJob(argv)

        cmd_val = test_lib.MakeBuiltinArgv(['wait', '-n'])
        status = self.wait_builtin.Run(cmd_val)
        log('status = %d', status)
        self.assertEqual(99, status)

        cmd_val = test_lib.MakeBuiltinArgv(['wait', '-n'])
        status = self.wait_builtin.Run(cmd_val)
        log('status = %d', status)
        self.assertEqual(127, status)

    # More tests:
    #
    #   wait $pipeline_pid - with pipeline leader, and other PID
    #   wait %pipeline_job
    #   wait -n on pipeline?  Does it return PIPESTATUS?
    #   wait with pipeline - should be OK
    #
    # Stopped jobs: does it print something interactively?


class PipelineJobListTest(_Common):
    """
    Like the above, but starts pipelines instead of individual processes.
    """

    def setUp(self):
        _SetupTest(self)

        self.wait_builtin = process_osh.Wait(self.waiter, self.job_list,
                                             self.mem, self.tracer,
                                             self.errfmt)

    def _RunBackgroundPipeline(self, argv_list):
        # Like Executor::RunBackgroundJob()
        pi = self._MakePipeline(argv_list, last_str='cat')
        pi.StartPipeline(self.waiter)
        pi.SetBackground()
        #self.mem.last_bg_pid = pid  # for $!
        job_id = self.job_list.RegisterJob(pi)  # show in 'jobs' list
        return pi, job_id

    def _StartPipelines(self, n):
        pipelines = []
        job_ids = []

        assert n < 10, n
        for i in xrange(1, n + 1):
            j = 10 - i  # count down
            argv_list = [['sleep', '0.0%d' % j], ['sh', '-c', 'exit %d' % j]]
            pi, job_id = self._RunBackgroundPipeline(argv_list)
            pipelines.append(pi)
            job_ids.append(job_id)

        log('pipelines %s', pipelines)
        log('job_ids %s', job_ids)

        return pipelines, job_ids

    def assertJobListLength(self, length):
        # 2 processes per pipeline in this test
        self.assertEqual(length * 2, len(self.job_list.child_procs))
        self.assertEqual(length, len(self.job_list.jobs))
        self.assertEqual(length, len(self.job_list.pid_to_job))

    def testWaitAll(self):
        """ wait """
        # Jobs list starts out empty
        self.assertJobListLength(0)

        # Fork 2 processes with &
        pids, job_ids = self._StartPipelines(2)

        # Now we have 2 jobs
        self.assertJobListLength(2)

        # Invoke the 'wait' builtin

        cmd_val = test_lib.MakeBuiltinArgv(['wait'])
        status = self.wait_builtin.Run(cmd_val)
        self.assertEqual(0, status)

        # TODO: fix bug
        return
        # Jobs list is now empty
        self.assertJobListLength(0)

    def testWaitNext(self):
        """ wait -n """
        # Jobs list starts out empty
        self.assertJobListLength(0)

        # Fork 2 pipelines with &
        pids, job_ids = self._StartPipelines(2)

        # Now we have 2 jobs
        self.assertJobListLength(2)

        ### 'wait -n'
        cmd_val = test_lib.MakeBuiltinArgv(['wait', '-n'])
        status = self.wait_builtin.Run(cmd_val)
        return
        self.assertEqual(8, status)

        # Jobs list now has 1 fewer job
        self.assertJobListLength(1)

        ### 'wait -n' again
        cmd_val = test_lib.MakeBuiltinArgv(['wait', '-n'])
        status = self.wait_builtin.Run(cmd_val)
        self.assertEqual(9, status)

        # Now zero
        self.assertJobListLength(0)

        ### 'wait -n' again
        cmd_val = test_lib.MakeBuiltinArgv(['wait', '-n'])
        status = self.wait_builtin.Run(cmd_val)
        self.assertEqual(127, status)

        # Still zero
        self.assertJobListLength(0)


if __name__ == '__main__':
    unittest.main()

# vim: sw=4
