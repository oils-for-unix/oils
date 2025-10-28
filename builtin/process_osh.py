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
from _devbuild.gen.syntax_asdl import loc, CompoundWord
from _devbuild.gen.runtime_asdl import (cmd_value, job_state_e, wait_status,
                                        wait_status_e)
from core import dev
from core import error
from core.error import e_usage, e_die_status
from core import process  # W1_EXITED, etc.
from core import pyos
from core import pyutil
from core import vm
from frontend import flag_util
from frontend import match
from frontend import typed_args
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import log, tagswitch, print_stderr

import posix_ as posix

from typing import TYPE_CHECKING, List, Tuple, Optional, cast
if TYPE_CHECKING:
    from core.process import Waiter, ExternalProgram, FdState
    from core import executor
    from core import state
    from display import ui

_ = log


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
        self.exec_opts = waiter.exec_opts

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        job_spec = ''  # Job spec for current job is the default
        if len(cmd_val.argv) > 1:
            job_spec = cmd_val.argv[1]

        job = self.job_list.JobFromSpec(job_spec)
        # note: the 'wait' builtin falls back to JobFromPid()
        if job is None:
            print_stderr('fg: No job to put in the foreground')
            return 1

        pgid = job.ProcessGroupId()
        assert pgid != process.INVALID_PGID, \
            'Processes put in the background should have a PGID'

        # Put the job's process group back into the foreground. GiveTerminal() must
        # be called before sending SIGCONT or else the process might immediately get
        # suspended again if it tries to read/write on the terminal.
        self.job_control.MaybeGiveTerminal(pgid)
        posix.killpg(pgid, SIGCONT)  # Send signal

        if self.exec_opts.interactive():
            print_stderr('[%%%d] PID %d Continued' % (job.job_id, pgid))

        # We are not using waitpid(WCONTINUE) and WIFCONTINUED() in
        # WaitForOne() -- it's an extension to POSIX that isn't necessary for 'fg'
        job.SetForeground()
        job.state = job_state_e.Running

        status = -1

        wait_st = job.JobWait(self.waiter)
        UP_wait_st = wait_st
        with tagswitch(wait_st) as case:
            if case(wait_status_e.Proc):
                wait_st = cast(wait_status.Proc, UP_wait_st)
                if wait_st.state == job_state_e.Exited:
                    self.job_list.PopChildProcess(job.PidForWait())
                    self.job_list.CleanupWhenJobExits(job)
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

        cmd_frag = typed_args.RequiredBlockAsFrag(cmd_val)
        return self.shell_ex.RunBackgroundJob(cmd_frag)


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

        cmd_frag = typed_args.RequiredBlockAsFrag(cmd_val)
        return self.shell_ex.RunSubshell(cmd_frag)


class Exec(vm._Builtin):

    def __init__(
            self,
            mem,  # type: state.Mem
            ext_prog,  # type: ExternalProgram
            fd_state,  # type: FdState
            search_path,  # type: executor.SearchPath
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
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

        environ = self.mem.GetEnv()
        if 0:
            log('E %r', environ)
            log('E %r', environ)
            log('ZZ %r', environ.get('ZZ'))
        i = arg_r.i
        cmd = cmd_val.argv[i]
        argv0_path = self.search_path.CachedLookup(cmd)
        if argv0_path is None:
            e_die_status(127, 'exec: %r not found' % cmd, cmd_val.arg_locs[1])

        # shift off 'exec', and remove typed args because they don't apply
        c2 = cmd_value.Argv(cmd_val.argv[i:], cmd_val.arg_locs[i:],
                            cmd_val.is_last_cmd, cmd_val.self_obj, None)

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

    def __init__(
            self,
            waiter,  # type: Waiter
            job_list,  #type: process.JobList
            mem,  # type: state.Mem
            tracer,  # type: dev.Tracer
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        self.waiter = waiter
        self.job_list = job_list
        self.mem = mem
        self.tracer = tracer
        self.errfmt = errfmt
        self.exec_opts = waiter.exec_opts

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        with dev.ctx_Tracer(self.tracer, 'wait', cmd_val.argv):
            return self._Run(cmd_val)

    def _WaitForJobs(self, job_ids, arg_locs):
        # type: (List[str], List[CompoundWord]) -> int

        # Get list of jobs.  Then we need to check if they are ALL stopped.
        # Returns the exit code of the last one on the COMMAND LINE, not the
        # exit code of last one to FINISH.

        jobs = []  # type: List[process.Job]
        for i, job_id in enumerate(job_ids):
            location = arg_locs[i]

            job = None  # type: Optional[process.Job]
            if job_id == '' or job_id.startswith('%'):
                job = self.job_list.JobFromSpec(job_id)

            if job is None:
                #log('JOB %s', job_id)
                # Does it look like a PID?
                try:
                    pid = int(job_id)
                except ValueError:
                    raise error.Usage(
                        'expected PID or jobspec, got %r' % job_id, location)

                job = self.job_list.JobFromPid(pid)
                #log('WAIT JOB %r', job)

            if job is None:
                self.errfmt.Print_("Job %s wasn't found" % job_id,
                                   blame_loc=location)
                return 127

            jobs.append(job)

        status = 1  # error
        for job in jobs:
            # polymorphic call: Process, Pipeline
            wait_st = job.JobWait(self.waiter)

            UP_wait_st = wait_st
            with tagswitch(wait_st) as case:
                if case(wait_status_e.Proc):
                    wait_st = cast(wait_status.Proc, UP_wait_st)
                    if wait_st.state == job_state_e.Exited:
                        self.job_list.PopChildProcess(job.PidForWait())
                        self.job_list.CleanupWhenJobExits(job)
                    status = wait_st.code

                elif case(wait_status_e.Pipeline):
                    wait_st = cast(wait_status.Pipeline, UP_wait_st)
                    # TODO: handle PIPESTATUS?  Is this right?
                    status = wait_st.codes[-1]

                    # It would be logical to set PIPESTATUS here, but it's NOT
                    # what other shells do
                    #
                    # I think PIPESTATUS is legacy, and we can design better
                    # YSH semantics
                    #self.mem.SetPipeStatus(wait_st.codes)

                elif case(wait_status_e.Cancelled):
                    wait_st = cast(wait_status.Cancelled, UP_wait_st)
                    status = 128 + wait_st.sig_num

                else:
                    raise AssertionError()

        # Return the last status
        return status

    def _WaitNext(self):
        # type: () -> int

        # Loop until there is one fewer process running, there's nothing to wait
        # for, or there's a signal
        n = self.job_list.NumRunning()
        if n == 0:
            status = 127
        else:
            target = n - 1
            status = 0
            while self.job_list.NumRunning() > target:
                result, w1_arg = self.waiter.WaitForOne()
                if result == process.W1_EXITED:
                    pid = w1_arg
                    pr = self.job_list.PopChildProcess(pid)
                    # TODO: background pipelines don't clean up properly,
                    # because only the last PID is registered in
                    # job_list.pid_to_job
                    self.job_list.CleanupWhenProcessExits(pid)

                    if pr is None:
                        if self.exec_opts.verbose_warn():
                            print_stderr(
                                "oils wait: PID %d exited, but oils didn't start it"
                                % pid)
                    else:
                        status = pr.status

                elif result == process.W1_NO_CHILDREN:
                    status = 127
                    break

                elif result == process.W1_CALL_INTR:  # signal
                    status = 128 + w1_arg
                    break

        return status

    def _Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('wait', cmd_val)
        arg = arg_types.wait(attrs.attrs)

        job_ids, arg_locs = arg_r.Rest2()

        if len(job_ids):
            # Note: -n and --all ignored in this case, like bash
            return self._WaitForJobs(job_ids, arg_locs)

        if arg.n:
            return self._WaitNext()

        # 'wait' or wait --all

        status = 0

        # Note: NumRunning() makes sure we ignore stopped processes, which
        # cause WaitForOne() to return
        while self.job_list.NumRunning() != 0:
            result, w1_arg = self.waiter.WaitForOne()
            if result == process.W1_EXITED:
                pid = w1_arg
                pr = self.job_list.PopChildProcess(pid)
                # TODO: background pipelines don't clean up properly, because
                # only the last PID is registered in job_list.pid_to_job
                self.job_list.CleanupWhenProcessExits(pid)

                if arg.verbose:
                    self.errfmt.PrintMessage(
                        '(wait) PID %d exited with status %d' %
                        (pid, pr.status), cmd_val.arg_locs[0])

                if pr.status != 0 and arg.all:  # YSH extension: respect failure
                    if arg.verbose:
                        self.errfmt.PrintMessage(
                            'wait --all: will fail with status 1')
                    status = 1  # set status, but keep waiting

            if result == process.W1_NO_CHILDREN:
                break  # status is 0

            if result == process.W1_CALL_INTR:
                status = 128 + w1_arg
                break

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
            # see: https://man7.org/linux/man-pages/man2/umask.2.html
            # NOTE: dash disables interrupts around the two umask() calls, but that
            # shouldn't be a concern for us.  Signal handlers won't call umask().
            mask = posix.umask(0)
            posix.umask(mask)
            print('0%03o' % mask)  # octal format
            return 0

        if len(argv) == 1:
            first_arg = argv[0]
            if first_arg[0].isdigit():
                try:
                    new_mask = int(first_arg, 8)
                except ValueError:
                    # NOTE: This also happens when we have '8' or '9' in the input.
                    print_stderr("oils warning: `%s` is not an octal number" %
                                 first_arg)
                    return 1

                posix.umask(new_mask)
                return 0
            elif first_arg[0] in "ugoa":
                # TODO: it's possible to avoid this extra syscall in cases where we don't care about
                # the initial value (ex: umask u=rwx,a=rwx) although it's non-trivial to determine
                # when, so it's probably not worth it
                initial_mask = posix.umask(0)
               
                # TODO: when to split first_arg? is this fine?
                ok, new_mask = self._MaskFromClauseList(initial_mask, first_arg.split(","))
                if not ok:
                    posix.umask(initial_mask)
                    return 1

                posix.umask(new_mask)
                return 0

            print_stderr(
                "oils warning: `%s` is an invalid symbolic mode operator" %
                first_arg[0])
            return 1

        e_usage("unexpected number of arguments", loc.Missing)

    def _MaskFromClauseList(self, mask, clause_list):
        # type: (int, list[str]) -> (bool, int)

        for clause in clause_list:
            ok, mask = self._SymbolicToOctal(mask, clause)
            if not ok:
                return False, 0 

        return True, mask 
        
    # TODO: update the naming convention here
    def _SymbolicToOctal(self, initial_mask, arg_component):
        # type: (int, str) -> (bool, int)

        # TODO: location highlighting would be nice
        if len(arg_component) == 0:
            print_stderr(
                "oils warning: symbolic mode operator cannot be empty")
            return False, 0
        elif arg_component[0] not in "ugoa":
            print_stderr(
                "oils warning: `%s` is an invalid symbolic mode operator" %
                arg_component[0])
            return False, 0
        elif len(arg_component) == 1:
            print_stderr(
                "oils warning: expected `=+-` after `%s` in symbolic mode operator"
                % arg_component[0])
            return False, 0
        elif arg_component[1] not in "=+-":
            print_stderr(
                "oils warning: `%s` is an invalid symbolic mode operator" %
                arg_component[1])
            return False, 0

        mask_digit = 0o7
        for ch in arg_component[2:]:
            if ch == 'r':
                mask_digit &= (0o7 - 0o4)
            elif ch == 'w':
                mask_digit &= (0o7 - 0o2)
            elif ch == 'x':
                mask_digit &= (0o7 - 0o1)
            else:
                print_stderr(
                    "oils warning: `%s` is an invalid symbolic mode character"
                    % ch)
                return False, 0

        if arg_component[0] == "u":
            area_mask = 0o700
            modifier = mask_digit << 6
        elif arg_component[0] == "g":
            area_mask = 0o070
            modifier = mask_digit << 3
        elif arg_component[0] == "o":
            area_mask = 0o007
            modifier = mask_digit
        elif arg_component[0] == "a":
            area_mask = 0o777
            modifier = (mask_digit << 6) | (mask_digit << 3) | mask_digit

        original_mask_area = initial_mask & ~area_mask
        if arg_component[1] == "=":
            new_mask = original_mask_area | modifier
        elif arg_component[1] == "+":
            new_mask = original_mask_area | (initial_mask & area_mask
                                             & modifier)
        elif arg_component[1] == "-":
            new_mask = original_mask_area | (initial_mask |
                                             (~modifier & area_mask))

        return True, new_mask


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
            if match.LooksLikeInteger(s):
                ok, big_int = mops.FromStr2(s)
                if not ok:
                    raise error.Usage('Integer too big: %s' % s, s_loc)
            else:
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

                print_stderr('oils: ulimit error: %s' % e)

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
                print_stderr('oils: ulimit error: %s' % pyutil.strerror(e))
                return 1

        return 0


# vim: sw=4
