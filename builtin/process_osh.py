#!/usr/bin/env python2
"""
builtin_process.py - Builtins that deal with processes or modify process state.

This is sort of the opposite of builtin_pure.py.
"""
from __future__ import print_function

import resource
from resource import (RLIM_INFINITY, RLIMIT_CORE, RLIMIT_CPU, RLIMIT_DATA,
                      RLIMIT_FSIZE, RLIMIT_NOFILE, RLIMIT_STACK, RLIMIT_AS)
from signal import SIGCONT

from _devbuild.gen import arg_types
from _devbuild.gen.syntax_asdl import loc
from _devbuild.gen.runtime_asdl import (cmd_value, job_state_e, wait_status,
                                        wait_status_e)
from core import dev
from core import error
from core.error import e_usage, e_die_status
from core import process  # W1_OK, W1_ECHILD
from core import pyos
from core import pyutil
from core import vm
from frontend import flag_util
from frontend import typed_args
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import log, tagswitch, print_stderr

import posix_ as posix

from typing import TYPE_CHECKING, List, Tuple, Optional, cast
if TYPE_CHECKING:
    from core.process import Waiter, ExternalProgram, FdState
    from core.state import Mem, SearchPath
    from display import ui


class Jobs(vm._Builtin):
    """List jobs."""

    def __init__(self, job_list):
        # type: (process.JobList) -> None
        self.job_list = job_list

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        attrs, arg_r = flag_util.ParseCmdVal('jobs', cmd_val)
        arg = arg_types.jobs(attrs.attrs)

        if arg.l:
            style = process.STYLE_LONG
        elif arg.p:
            style = process.STYLE_PID_ONLY
        else:
            style = process.STYLE_DEFAULT

        self.job_list.DisplayJobs(style)

        if arg.debug:
            self.job_list.DebugPrint()

        return 0


class Fg(vm._Builtin):
    """Put a job in the foreground."""

    def __init__(self, job_control, job_list, waiter):
        # type: (process.JobControl, process.JobList, Waiter) -> None
        self.job_control = job_control
        self.job_list = job_list
        self.waiter = waiter

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        job_spec = ''  # get current job by default
        if len(cmd_val.argv) > 1:
            job_spec = cmd_val.argv[1]

        job = self.job_list.GetJobWithSpec(job_spec)
        if job is None:
            log('No job to put in the foreground')
            return 1

        pgid = job.ProcessGroupId()
        assert pgid != process.INVALID_PGID, \
            'Processes put in the background should have a PGID'

        # TODO: Print job ID rather than the PID
        log('Continue PID %d', pgid)
        # Put the job's process group back into the foreground. GiveTerminal() must
        # be called before sending SIGCONT or else the process might immediately get
        # suspsended again if it tries to read/write on the terminal.
        self.job_control.MaybeGiveTerminal(pgid)
        job.SetForeground()
        # needed for Wait() loop to work
        job.state = job_state_e.Running
        posix.killpg(pgid, SIGCONT)

        status = -1
        wait_st = job.JobWait(self.waiter)
        UP_wait_st = wait_st
        with tagswitch(wait_st) as case:
            if case(wait_status_e.Proc):
                wait_st = cast(wait_status.Proc, UP_wait_st)
                status = wait_st.code

            elif case(wait_status_e.Pipeline):
                wait_st = cast(wait_status.Pipeline, UP_wait_st)
                # TODO: handle PIPESTATUS?  Is this right?
                status = wait_st.codes[-1]

            elif case(wait_status_e.Cancelled):
                wait_st = cast(wait_status.Cancelled, UP_wait_st)
                status = 128 + wait_st.sig_num

            else:
                raise AssertionError()

        return status


class Bg(vm._Builtin):
    """Put a job in the background."""

    def __init__(self, job_list):
        # type: (process.JobList) -> None
        self.job_list = job_list

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        # How does this differ from 'fg'?  It doesn't wait and it sets controlling
        # terminal?

        raise error.Usage("isn't implemented", loc.Missing)


class Fork(vm._Builtin):

    def __init__(self, shell_ex):
        # type: (vm._Executor) -> None
        self.shell_ex = shell_ex

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('fork',
                                         cmd_val,
                                         accept_typed_args=True)

        arg, location = arg_r.Peek2()
        if arg is not None:
            e_usage('got unexpected argument %r' % arg, location)

        cmd = typed_args.OptionalBlock(cmd_val)
        if cmd is None:
            e_usage('expected a block', loc.Missing)

        return self.shell_ex.RunBackgroundJob(cmd)


class ForkWait(vm._Builtin):

    def __init__(self, shell_ex):
        # type: (vm._Executor) -> None
        self.shell_ex = shell_ex

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('forkwait',
                                         cmd_val,
                                         accept_typed_args=True)
        arg, location = arg_r.Peek2()
        if arg is not None:
            e_usage('got unexpected argument %r' % arg, location)

        cmd = typed_args.OptionalBlock(cmd_val)
        if cmd is None:
            e_usage('expected a block', loc.Missing)

        return self.shell_ex.RunSubshell(cmd)


class Exec(vm._Builtin):

    def __init__(self, mem, ext_prog, fd_state, search_path, errfmt):
        # type: (Mem, ExternalProgram, FdState, SearchPath, ui.ErrorFormatter) -> None
        self.mem = mem
        self.ext_prog = ext_prog
        self.fd_state = fd_state
        self.search_path = search_path
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('exec', cmd_val)

        # Apply redirects in this shell.  # NOTE: Redirects were processed earlier.
        if arg_r.AtEnd():
            self.fd_state.MakePermanent()
            return 0

        environ = self.mem.GetExported()
        i = arg_r.i
        cmd = cmd_val.argv[i]
        argv0_path = self.search_path.CachedLookup(cmd)
        if argv0_path is None:
            e_die_status(127, 'exec: %r not found' % cmd, cmd_val.arg_locs[1])

        # shift off 'exec', and remove typed args because they don't apply
        c2 = cmd_value.Argv(cmd_val.argv[i:], cmd_val.arg_locs[i:],
                            cmd_val.is_last_cmd, None)

        self.ext_prog.Exec(argv0_path, c2, environ)  # NEVER RETURNS
        # makes mypy and C++ compiler happy
        raise AssertionError('unreachable')


class Wait(vm._Builtin):
    """
    wait: wait [-n] [id ...]
        Wait for job completion and return exit status.

        Waits for each process identified by an ID, which may be a process ID or a
        job specification, and reports its termination status.  If ID is not
        given, waits for all currently active child processes, and the return
        status is zero.  If ID is a a job specification, waits for all processes
        in that job's pipeline.

        If the -n option is supplied, waits for the next job to terminate and
        returns its exit status.

        Exit Status:
        Returns the status of the last ID; fails if ID is invalid or an invalid
        option is given.
    """

    def __init__(self, waiter, job_list, mem, tracer, errfmt):
        # type: (Waiter, process.JobList, Mem, dev.Tracer, ui.ErrorFormatter) -> None
        self.waiter = waiter
        self.job_list = job_list
        self.mem = mem
        self.tracer = tracer
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        with dev.ctx_Tracer(self.tracer, 'wait', cmd_val.argv):
            return self._Run(cmd_val)

    def _Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('wait', cmd_val)
        arg = arg_types.wait(attrs.attrs)

        job_ids, arg_locs = arg_r.Rest2()

        if arg.n:
            # Loop until there is one fewer process running, there's nothing to wait
            # for, or there's a signal
            n = self.job_list.NumRunning()
            if n == 0:
                status = 127
            else:
                target = n - 1
                status = 0
                while self.job_list.NumRunning() > target:
                    result = self.waiter.WaitForOne()
                    if result == process.W1_OK:
                        status = self.waiter.last_status
                    elif result == process.W1_ECHILD:
                        # nothing to wait for, or interrupted
                        status = 127
                        break
                    elif result >= 0:  # signal
                        status = 128 + result
                        break

            return status

        if len(job_ids) == 0:
            #log('*** wait')

            # BUG: If there is a STOPPED process, this will hang forever, because we
            # don't get ECHILD.  Not sure it matters since you can now Ctrl-C it.
            # But how to fix this?

            status = 0
            while self.job_list.NumRunning() != 0:
                result = self.waiter.WaitForOne()
                if result == process.W1_ECHILD:
                    # nothing to wait for, or interrupted.  status is 0
                    break
                elif result >= 0:  # signal
                    status = 128 + result
                    break

            return status

        # Get list of jobs.  Then we need to check if they are ALL stopped.
        # Returns the exit code of the last one on the COMMAND LINE, not the exit
        # code of last one to FINISH.
        jobs = []  # type: List[process.Job]
        for i, job_id in enumerate(job_ids):
            location = arg_locs[i]

            job = None  # type: Optional[process.Job]
            if job_id == '' or job_id.startswith('%'):
                job = self.job_list.GetJobWithSpec(job_id)

            if job is None:
                # Does it look like a PID?
                try:
                    pid = int(job_id)
                except ValueError:
                    raise error.Usage(
                        'expected PID or jobspec, got %r' % job_id, location)

                job = self.job_list.ProcessFromPid(pid)

            if job is None:
                self.errfmt.Print_("%s isn't a child of this shell" % job_id,
                                   blame_loc=location)
                return 127

            jobs.append(job)

        status = 1  # error
        for job in jobs:
            wait_st = job.JobWait(self.waiter)
            UP_wait_st = wait_st
            with tagswitch(wait_st) as case:
                if case(wait_status_e.Proc):
                    wait_st = cast(wait_status.Proc, UP_wait_st)
                    status = wait_st.code

                elif case(wait_status_e.Pipeline):
                    wait_st = cast(wait_status.Pipeline, UP_wait_st)
                    # TODO: handle PIPESTATUS?  Is this right?
                    status = wait_st.codes[-1]

                elif case(wait_status_e.Cancelled):
                    wait_st = cast(wait_status.Cancelled, UP_wait_st)
                    status = 128 + wait_st.sig_num

                else:
                    raise AssertionError()

        return status


class Umask(vm._Builtin):

    def __init__(self):
        # type: () -> None
        """Dummy constructor for mycpp."""
        pass

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        argv = cmd_val.argv[1:]
        if len(argv) == 0:
            # umask() has a dumb API: you can't get it without modifying it first!
            # NOTE: dash disables interrupts around the two umask() calls, but that
            # shouldn't be a concern for us.  Signal handlers won't call umask().
            mask = posix.umask(0)
            posix.umask(mask)  #
            print('0%03o' % mask)  # octal format
            return 0

        if len(argv) == 1:
            a = argv[0]
            try:
                new_mask = int(a, 8)
            except ValueError:
                # NOTE: This also happens when we have '8' or '9' in the input.
                print_stderr(
                    "osh warning: umask with symbolic input isn't implemented")
                return 1

            posix.umask(new_mask)
            return 0

        e_usage('umask: unexpected arguments', loc.Missing)


def _LimitString(lim, factor):
    # type: (mops.BigInt, int) -> str
    if mops.Equal(lim, mops.FromC(RLIM_INFINITY)):
        return 'unlimited'
    else:
        i = mops.Div(lim, mops.IntWiden(factor))
        return mops.ToStr(i)


class Ulimit(vm._Builtin):

    def __init__(self):
        # type: () -> None
        """Dummy constructor for mycpp."""

        self._table = None  # type: List[Tuple[str, int, int, str]]

    def _Table(self):
        # type: () -> List[Tuple[str, int, int, str]]

        # POSIX 2018
        #
        # https://pubs.opengroup.org/onlinepubs/9699919799/functions/getrlimit.html
        if self._table is None:
            # This table matches _ULIMIT_RESOURCES in frontend/flag_def.py

            # flag, RLIMIT_X, factor, description
            self._table = [
                # Following POSIX and most shells except bash, -f is in
                # blocks of 512 bytes
                ('-c', RLIMIT_CORE, 512, 'core dump size'),
                ('-d', RLIMIT_DATA, 1024, 'data segment size'),
                ('-f', RLIMIT_FSIZE, 512, 'file size'),
                ('-n', RLIMIT_NOFILE, 1, 'file descriptors'),
                ('-s', RLIMIT_STACK, 1024, 'stack size'),
                ('-t', RLIMIT_CPU, 1, 'CPU seconds'),
                ('-v', RLIMIT_AS, 1024, 'address space size'),
            ]

        return self._table

    def _FindFactor(self, what):
        # type: (int) -> int
        for _, w, factor, _ in self._Table():
            if w == what:
                return factor
        raise AssertionError()

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        attrs, arg_r = flag_util.ParseCmdVal('ulimit', cmd_val)
        arg = arg_types.ulimit(attrs.attrs)

        what = 0
        num_what_flags = 0

        if arg.c:
            what = RLIMIT_CORE
            num_what_flags += 1

        if arg.d:
            what = RLIMIT_DATA
            num_what_flags += 1

        if arg.f:
            what = RLIMIT_FSIZE
            num_what_flags += 1

        if arg.n:
            what = RLIMIT_NOFILE
            num_what_flags += 1

        if arg.s:
            what = RLIMIT_STACK
            num_what_flags += 1

        if arg.t:
            what = RLIMIT_CPU
            num_what_flags += 1

        if arg.v:
            what = RLIMIT_AS
            num_what_flags += 1

        if num_what_flags > 1:
            raise error.Usage(
                'can only handle one resource at a time; got too many flags',
                cmd_val.arg_locs[0])

        # Print all
        show_all = arg.a or arg.all
        if show_all:
            if num_what_flags > 0:
                raise error.Usage("doesn't accept resource flags with -a",
                                  cmd_val.arg_locs[0])

            extra, extra_loc = arg_r.Peek2()
            if extra is not None:
                raise error.Usage('got extra arg with -a', extra_loc)

            # Worst case 20 == len(str(2**64))
            fmt = '%5s %15s %15s %7s  %s'
            print(fmt % ('FLAG', 'SOFT', 'HARD', 'FACTOR', 'DESC'))
            for flag, what, factor, desc in self._Table():
                soft, hard = pyos.GetRLimit(what)

                soft2 = _LimitString(soft, factor)
                hard2 = _LimitString(hard, factor)
                print(fmt % (flag, soft2, hard2, str(factor), desc))

            return 0

        if num_what_flags == 0:
            what = RLIMIT_FSIZE  # -f is the default

        s, s_loc = arg_r.Peek2()

        if s is None:
            factor = self._FindFactor(what)
            soft, hard = pyos.GetRLimit(what)
            if arg.H:
                print(_LimitString(hard, factor))
            else:
                print(_LimitString(soft, factor))
            return 0

        # Set the given resource
        if s == 'unlimited':
            # In C, RLIM_INFINITY is rlim_t
            limit = mops.FromC(RLIM_INFINITY)
        else:
            try:
                big_int = mops.FromStr(s)
            except ValueError as e:
                raise error.Usage(
                    "expected a number or 'unlimited', got %r" % s, s_loc)

            if mops.Greater(mops.IntWiden(0), big_int):
                raise error.Usage(
                    "doesn't accept negative numbers, got %r" % s, s_loc)

            factor = self._FindFactor(what)

            fac = mops.IntWiden(factor)
            limit = mops.Mul(big_int, fac)

            # Overflow check like bash does
            # TODO: This should be replaced with a different overflow check
            # when we have arbitrary precision integers
            if not mops.Equal(mops.Div(limit, fac), big_int):
                #log('div %s', mops.ToStr(mops.Div(limit, fac)))
                raise error.Usage(
                    'detected integer overflow: %s' % mops.ToStr(big_int),
                    s_loc)

        arg_r.Next()
        extra2, extra_loc2 = arg_r.Peek2()
        if extra2 is not None:
            raise error.Usage('got extra arg', extra_loc2)

        # Now set the resource
        soft, hard = pyos.GetRLimit(what)

        # For error message
        old_soft = soft
        old_hard = hard

        # Bash behavior: manipulate both, unless a flag is parsed.  This
        # differs from zsh!
        if not arg.S and not arg.H:
            soft = limit
            hard = limit
        if arg.S:
            soft = limit
        if arg.H:
            hard = limit

        if mylib.PYTHON:
            try:
                pyos.SetRLimit(what, soft, hard)
            except OverflowError:  # only happens in CPython
                raise error.Usage('detected overflow', s_loc)
            except (ValueError, resource.error) as e:
                # Annoying: Python binding changes IOError -> ValueError

                print_stderr('ulimit error: %s' % e)

                # Extra info we could expose in C++ too
                print_stderr('soft=%s hard=%s -> soft=%s hard=%s' % (
                    _LimitString(old_soft, factor),
                    _LimitString(old_hard, factor),
                    _LimitString(soft, factor),
                    _LimitString(hard, factor),
                ))
                return 1
        else:
            try:
                pyos.SetRLimit(what, soft, hard)
            except (IOError, OSError) as e:
                print_stderr('ulimit error: %s' % pyutil.strerror(e))
                return 1

        return 0


# vim: sw=4
