"""executor.py."""
from __future__ import print_function

from errno import EINTR

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.option_asdl import builtin_i
from _devbuild.gen.runtime_asdl import RedirValue, trace
from _devbuild.gen.syntax_asdl import (
    command,
    command_e,
    CommandSub,
    CompoundWord,
    loc,
    loc_t,
)
from _devbuild.gen.value_asdl import value
from builtin import hay_ysh
from core import dev
from core import error
from core import process
from core.error import e_die, e_die_status
from core import pyos
from core import state
from core import ui
from core import vm
from frontend import consts
from frontend import lexer
from mycpp.mylib import log

import posix_ as posix

from typing import cast, Dict, List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import (cmd_value, CommandStatus,
                                            StatusArray)
    from _devbuild.gen.syntax_asdl import command_t
    from builtin import trap_osh
    from core import optview
    from core import state
    from core.vm import _Builtin

_ = log


class _ProcessSubFrame(object):
    """To keep track of diff <(cat 1) <(cat 2) > >(tac)"""

    def __init__(self):
        # type: () -> None

        # These objects appear unconditionally in the main loop, and aren't
        # commonly used, so we manually optimize [] into None.

        self._to_wait = []  # type: List[process.Process]
        self._to_close = []  # type: List[int]  # file descriptors
        self._locs = []  # type: List[loc_t]
        self._modified = False

    def WasModified(self):
        # type: () -> bool
        return self._modified

    def Append(self, p, fd, status_loc):
        # type: (process.Process, int, loc_t) -> None
        self._modified = True

        self._to_wait.append(p)
        self._to_close.append(fd)
        self._locs.append(status_loc)

    def MaybeWaitOnProcessSubs(self, waiter, status_array):
        # type: (process.Waiter, StatusArray) -> None

        # Wait in the same order that they were evaluated.  That seems fine.
        for fd in self._to_close:
            posix.close(fd)

        codes = []  # type: List[int]
        locs = []  # type: List[loc_t]
        for i, p in enumerate(self._to_wait):
            #log('waiting for %s', p)
            st = p.Wait(waiter)
            codes.append(st)
            locs.append(self._locs[i])

        status_array.codes = codes
        status_array.locs = locs


# Big flgas for RunSimpleCommand
DO_FORK = 1 << 1
NO_CALL_PROCS = 1 << 2  # command ls suppresses function lookup
USE_DEFAULT_PATH = 1 << 3  # for command -p ls changes the path

# Copied from var.c in dash
DEFAULT_PATH = [
    '/usr/local/sbin', '/usr/local/bin', '/usr/sbin', '/usr/bin', '/sbin',
    '/bin'
]


class ShellExecutor(vm._Executor):
    """An executor combined with the OSH language evaluators in osh/ to create
    a shell interpreter."""

    def __init__(
            self,
            mem,  # type: state.Mem
            exec_opts,  # type: optview.Exec
            mutable_opts,  # type: state.MutableOpts
            procs,  # type: Dict[str, value.Proc]
            hay_state,  # type: hay_ysh.HayState
            builtins,  # type: Dict[int, _Builtin]
            search_path,  # type: state.SearchPath
            ext_prog,  # type: process.ExternalProgram
            waiter,  # type: process.Waiter
            tracer,  # type: dev.Tracer
            job_control,  # type: process.JobControl
            job_list,  # type: process.JobList
            fd_state,  # type: process.FdState
            trap_state,  # type: trap_osh.TrapState
            errfmt  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        vm._Executor.__init__(self)
        self.mem = mem
        self.exec_opts = exec_opts
        self.mutable_opts = mutable_opts  # for IsDisabled(), not mutating
        self.procs = procs
        self.hay_state = hay_state
        self.builtins = builtins
        self.search_path = search_path
        self.ext_prog = ext_prog
        self.waiter = waiter
        self.tracer = tracer
        self.multi_trace = tracer.multi_trace
        self.job_control = job_control
        # sleep 5 & puts a (PID, job#) entry here.  And then "jobs" displays it.
        self.job_list = job_list
        self.fd_state = fd_state
        self.trap_state = trap_state
        self.errfmt = errfmt
        self.process_sub_stack = []  # type: List[_ProcessSubFrame]
        self.clean_frame_pool = []  # type: List[_ProcessSubFrame]

        # When starting a pipeline in the foreground, we need to pass a handle to it
        # through the evaluation of the last node back to ourselves for execution.
        # We use this handle to make sure any processes forked for the last part of
        # the pipeline are placed into the same process group as the rest of the
        # pipeline. Since there is, by design, only ever one foreground pipeline and
        # any pipelines started within subshells run in their parent's process
        # group, we only need one pointer here, not some collection.
        self.fg_pipeline = None  # type: Optional[process.Pipeline]

    def CheckCircularDeps(self):
        # type: () -> None
        assert self.cmd_ev is not None

    def _MakeProcess(self, node, inherit_errexit=True):
        # type: (command_t, bool) -> process.Process
        """Assume we will run the node in another process.

        Return a process.
        """
        UP_node = node
        if node.tag() == command_e.ControlFlow:
            node = cast(command.ControlFlow, UP_node)
            # Pipeline or subshells with control flow are invalid, e.g.:
            # - break | less
            # - continue | less
            # - ( return )
            # NOTE: This could be done at parse time too.
            if node.keyword.id != Id.ControlFlow_Exit:
                e_die(
                    'Invalid control flow %r in pipeline / subshell / background'
                    % lexer.TokenVal(node.keyword), node.keyword)

        # NOTE: If ErrExit(), we could be verbose about subprogram errors?  This
        # only really matters when executing 'exit 42', because the child shell
        # inherits errexit and will be verbose.  Other notes:
        #
        # - We might want errors to fit on a single line so they don't get #
        #   interleaved.
        # - We could turn the `exit` builtin into a error.FatalRuntime exception
        #   and get this check for "free".
        thunk = process.SubProgramThunk(self.cmd_ev,
                                        node,
                                        self.trap_state,
                                        self.multi_trace,
                                        inherit_errexit=inherit_errexit)
        p = process.Process(thunk, self.job_control, self.job_list,
                            self.tracer)
        return p

    def RunBuiltin(self, builtin_id, cmd_val):
        # type: (int, cmd_value.Argv) -> int
        """Run a builtin.

        Also called by the 'builtin' builtin.
        """
        self.tracer.OnBuiltin(builtin_id, cmd_val.argv)

        builtin_func = self.builtins[builtin_id]

        with vm.ctx_FlushStdout():
            # note: could be second word, like 'builtin read'
            with ui.ctx_Location(self.errfmt, cmd_val.arg_locs[0]):
                try:
                    status = builtin_func.Run(cmd_val)
                    assert isinstance(status, int)
                except error.Usage as e:
                    arg0 = cmd_val.argv[0]
                    # e.g. 'type' doesn't accept flag '-x'
                    self.errfmt.PrefixPrint(e.msg, '%r ' % arg0, e.location)
                    status = 2  # consistent error code for usage error

        return status

    def RunSimpleCommand(self, cmd_val, cmd_st, run_flags):
        # type: (cmd_value.Argv, CommandStatus, int) -> int
        """Run builtins, functions, external commands.

        Possible variations:
        - YSH might have different, simpler rules.  No special builtins, etc.
        - YSH might have OILS_PATH = :| /bin /usr/bin | or something.
        - Interpreters might want to define all their own builtins.

        Args:
          call_procs: whether to look up procs.
        """
        argv = cmd_val.argv
        if len(cmd_val.arg_locs):
            arg0_loc = cmd_val.arg_locs[0]  # type: loc_t
        else:
            arg0_loc = loc.Missing

        # This happens when you write "$@" but have no arguments.
        if len(argv) == 0:
            if self.exec_opts.strict_argv():
                e_die("Command evaluated to an empty argv array", arg0_loc)
            else:
                return 0  # status 0, or skip it?

        arg0 = argv[0]

        builtin_id = consts.LookupAssignBuiltin(arg0)
        if builtin_id != consts.NO_INDEX:
            # command readonly is disallowed, for technical reasons.  Could relax it
            # later.
            self.errfmt.Print_("Can't run assignment builtin recursively",
                               arg0_loc)
            return 1

        builtin_id = consts.LookupSpecialBuiltin(arg0)
        if builtin_id != consts.NO_INDEX:
            cmd_st.show_code = True  # this is a "leaf" for errors
            status = self.RunBuiltin(builtin_id, cmd_val)
            # TODO: Enable this and fix spec test failures.
            # Also update _SPECIAL_BUILTINS in osh/builtin.py.
            #if status != 0:
            #  e_die_status(status, 'special builtin failed')
            return status

        call_procs = not (run_flags & NO_CALL_PROCS)
        # Builtins like 'true' can be redefined as functions.
        if call_procs:
            proc_node = self.procs.get(arg0)
            if proc_node is not None:
                if self.exec_opts.strict_errexit():
                    disabled_tok = self.mutable_opts.ErrExitDisabledToken()
                    if disabled_tok:
                        self.errfmt.Print_(
                            'errexit was disabled for this construct',
                            disabled_tok)
                        self.errfmt.StderrLine('')
                        e_die(
                            "Can't run a proc while errexit is disabled. "
                            "Use 'try' or wrap it in a process with $0 myproc",
                            arg0_loc)

                with dev.ctx_Tracer(self.tracer, 'proc', argv):
                    # NOTE: Functions could call 'exit 42' directly, etc.
                    status = self.cmd_ev.RunProc(proc_node, cmd_val)
                return status

        # Notes:
        # - procs shadow hay names
        # - hay names shadow normal builtins?  Should we limit to CAPS or no?
        if self.hay_state.Resolve(arg0):
            return self.RunBuiltin(builtin_i.haynode, cmd_val)

        builtin_id = consts.LookupNormalBuiltin(arg0)

        if self.exec_opts._running_hay():
            # Hay: limit the builtins that can be run
            # - declare 'use dialect'
            # - echo and write for debugging
            # - no JSON?
            if builtin_id in (builtin_i.haynode, builtin_i.use, builtin_i.echo,
                              builtin_i.write):
                cmd_st.show_code = True  # this is a "leaf" for errors
                return self.RunBuiltin(builtin_id, cmd_val)

            self.errfmt.Print_('Unknown command %r while running hay' % arg0,
                               arg0_loc)
            return 127

        if builtin_id != consts.NO_INDEX:
            cmd_st.show_code = True  # this is a "leaf" for errors
            return self.RunBuiltin(builtin_id, cmd_val)

        environ = self.mem.GetExported()  # Include temporary variables

        if cmd_val.typed_args:
            e_die(
                '%r appears to be external. External commands don\'t accept typed args (OILS-ERR-200)'
                % arg0, cmd_val.typed_args.left)

        # Resolve argv[0] BEFORE forking.
        if run_flags & USE_DEFAULT_PATH:
            argv0_path = state.LookupExecutable(arg0, DEFAULT_PATH)
        else:
            argv0_path = self.search_path.CachedLookup(arg0)
        if argv0_path is None:
            self.errfmt.Print_('%r not found' % arg0, arg0_loc)
            return 127

        # Normal case: ls /
        if run_flags & DO_FORK:
            thunk = process.ExternalThunk(self.ext_prog, argv0_path, cmd_val,
                                          environ)
            p = process.Process(thunk, self.job_control, self.job_list,
                                self.tracer)

            if self.job_control.Enabled():
                if self.fg_pipeline is not None:
                    pgid = self.fg_pipeline.ProcessGroupId()
                    # If job control is enabled, this should be true
                    assert pgid != process.INVALID_PGID

                    change = process.SetPgid(pgid, self.tracer)
                    self.fg_pipeline = None  # clear to avoid confusion in subshells
                else:
                    change = process.SetPgid(process.OWN_LEADER, self.tracer)
                p.AddStateChange(change)

            status = p.RunProcess(self.waiter, trace.External(cmd_val.argv))

            # this is close to a "leaf" for errors
            # problem: permission denied EACCESS prints duplicate messages
            # TODO: add message command 'ls' failed
            cmd_st.show_code = True

            return status

        self.tracer.OnExec(cmd_val.argv)

        # Already forked for pipeline: ls / | wc -l
        self.ext_prog.Exec(argv0_path, cmd_val, environ)  # NEVER RETURNS

        raise AssertionError('for -Wreturn-type in C++')

    def RunBackgroundJob(self, node):
        # type: (command_t) -> int
        """For & etc."""
        # Special case for pipeline.  There is some evidence here:
        # https://www.gnu.org/software/libc/manual/html_node/Launching-Jobs.html#Launching-Jobs
        #
        #  "You can either make all the processes in the process group be children
        #  of the shell process, or you can make one process in group be the
        #  ancestor of all the other processes in that group. The sample shell
        #  program presented in this chapter uses the first approach because it
        #  makes bookkeeping somewhat simpler."
        UP_node = node

        if UP_node.tag() == command_e.Pipeline:
            node = cast(command.Pipeline, UP_node)
            pi = process.Pipeline(self.exec_opts.sigpipe_status_ok(),
                                  self.job_control, self.job_list, self.tracer)
            for child in node.children:
                p = self._MakeProcess(child)
                p.Init_ParentPipeline(pi)
                pi.Add(p)

            pi.StartPipeline(self.waiter)
            pi.SetBackground()
            last_pid = pi.LastPid()
            self.mem.last_bg_pid = last_pid  # for $!

            self.job_list.AddJob(pi)  # show in 'jobs' list

        else:
            # Problem: to get the 'set -b' behavior of immediate notifications, we
            # have to register SIGCHLD.  But then that introduces race conditions.
            # If we haven't called Register yet, then we won't know who to notify.

            p = self._MakeProcess(node)
            if self.job_control.Enabled():
                p.AddStateChange(
                    process.SetPgid(process.OWN_LEADER, self.tracer))

            p.SetBackground()
            pid = p.StartProcess(trace.Fork)
            self.mem.last_bg_pid = pid  # for $!
            self.job_list.AddJob(p)  # show in 'jobs' list
        return 0

    def RunPipeline(self, node, status_out):
        # type: (command.Pipeline, CommandStatus) -> None

        pi = process.Pipeline(self.exec_opts.sigpipe_status_ok(),
                              self.job_control, self.job_list, self.tracer)

        # initialized with CommandStatus.CreateNull()
        pipe_locs = []  # type: List[loc_t]

        # First n-1 processes (which is empty when n == 1)
        n = len(node.children)
        for i in xrange(n - 1):
            child = node.children[i]

            # TODO: determine these locations at parse time?
            pipe_locs.append(loc.Command(child))

            p = self._MakeProcess(child)
            p.Init_ParentPipeline(pi)
            pi.Add(p)

        last_child = node.children[n - 1]
        # Last piece of code is in THIS PROCESS.  'echo foo | read line; echo $line'
        pi.AddLast((self.cmd_ev, last_child))
        pipe_locs.append(loc.Command(last_child))

        with dev.ctx_Tracer(self.tracer, 'pipeline', None):
            pi.StartPipeline(self.waiter)
            self.fg_pipeline = pi
            status_out.pipe_status = pi.RunLastPart(self.waiter, self.fd_state)
            self.fg_pipeline = None  # clear in case we didn't end up forking

        status_out.pipe_locs = pipe_locs

    def RunSubshell(self, node):
        # type: (command_t) -> int
        p = self._MakeProcess(node)
        if self.job_control.Enabled():
            p.AddStateChange(process.SetPgid(process.OWN_LEADER, self.tracer))

        return p.RunProcess(self.waiter, trace.ForkWait)

    def RunCommandSub(self, cs_part):
        # type: (CommandSub) -> str

        if not self.exec_opts._allow_command_sub():
            # _allow_command_sub is used in two places.  Only one of them turns off _allow_process_sub
            if not self.exec_opts._allow_process_sub():
                why = "status wouldn't be checked (strict_errexit)"
            else:
                why = 'eval_unsafe_arith is off'

            e_die("Command subs not allowed here because %s" % why,
                  loc.WordPart(cs_part))

        node = cs_part.child

        # Hack for weird $(<file) construct
        if node.tag() == command_e.Simple:
            simple = cast(command.Simple, node)
            # Detect '< file'
            if (len(simple.words) == 0 and len(simple.redirects) == 1 and
                    simple.redirects[0].op.id == Id.Redir_Less):
                # change it to __cat < file
                # TODO: change to 'internal cat' (issue 1013)
                tok = lexer.DummyToken(Id.Lit_Chars, '__cat')
                cat_word = CompoundWord([tok])
                # MUTATE the command.Simple node.  This will only be done the first
                # time in the parent process.
                simple.words.append(cat_word)

        p = self._MakeProcess(node,
                              inherit_errexit=self.exec_opts.inherit_errexit())
        # Shell quirk: Command subs remain part of the shell's process group, so we
        # don't use p.AddStateChange(process.SetPgid(...))

        r, w = posix.pipe()
        p.AddStateChange(process.StdoutToPipe(r, w))

        p.StartProcess(trace.CommandSub)
        #log('Command sub started %d', pid)

        chunks = []  # type: List[str]
        posix.close(w)  # not going to write
        while True:
            n, err_num = pyos.Read(r, 4096, chunks)

            if n < 0:
                if err_num == EINTR:
                    pass  # retry
                else:
                    # Like the top level IOError handler
                    e_die_status(
                        2,
                        'osh I/O error (read): %s' % posix.strerror(err_num))

            elif n == 0:  # EOF
                break
        posix.close(r)

        status = p.Wait(self.waiter)

        # OSH has the concept of aborting in the middle of a WORD.  We're not
        # waiting until the command is over!
        if self.exec_opts.command_sub_errexit():
            if status != 0:
                msg = 'Command Sub exited with status %d' % status
                raise error.ErrExit(status, msg, loc.WordPart(cs_part))

        else:
            # Set a flag so we check errexit at the same time as bash.  Example:
            #
            # a=$(false)
            # echo foo  # no matter what comes here, the flag is reset
            #
            # Set ONLY until this command node has finished executing.

            # HACK: move this
            self.cmd_ev.check_command_sub_status = True
            self.mem.SetLastStatus(status)

        # Runtime errors test case: # $("echo foo > $@")
        # Why rstrip()?
        # https://unix.stackexchange.com/questions/17747/why-does-shell-command-substitution-gobble-up-a-trailing-newline-char
        return ''.join(chunks).rstrip('\n')

    def RunProcessSub(self, cs_part):
        # type: (CommandSub) -> str
        """Process sub creates a forks a process connected to a pipe.

        The pipe is typically passed to another process via a /dev/fd/$FD path.

        Life cycle of a process substitution:

        1. Start with this code

          diff <(seq 3) <(seq 4)

        2. To evaluate the command line, we evaluate every word.  The
        NormalWordEvaluator this method, RunProcessSub(), which does 3 things:

          a. Create a pipe(), getting r and w
          b. Starts the seq process, which inherits r and w
             It has a StdoutToPipe() redirect, which means that it dup2(w, 1)
             and close(r)
          c. Close the w FD, because neither the shell or 'diff' will write to it.
             However we must retain 'r', because 'diff' hasn't opened /dev/fd yet!
          d. We evaluate <(seq 3) to /dev/fd/$r, so "diff" can read from it

        3. Now we're done evaluating every word, so we know the command line of
           diff, which looks like

          diff /dev/fd/64 /dev/fd/65

        Those are the FDs for the read ends of the pipes we created.

        4. diff inherits a copy of the read end of bot pipes.  But it actually
        calls open() both files passed as argv.  (I think this is fine.)

        5. wait() for the diff process.

        6. The shell closes both the read ends of both pipes.  Neither us or
        'diffd' will read again.

        7. The shell waits for both 'seq' processes.

        Related:
          shopt -s process_sub_fail
          _process_sub_status
        """
        cs_loc = loc.WordPart(cs_part)

        if not self.exec_opts._allow_process_sub():
            e_die(
                "Process subs not allowed here because status wouldn't be checked (strict_errexit)",
                cs_loc)

        p = self._MakeProcess(cs_part.child)

        r, w = posix.pipe()
        #log('pipe = %d, %d', r, w)

        op_id = cs_part.left_token.id
        if op_id == Id.Left_ProcSubIn:
            # Example: cat < <(head foo.txt)
            #
            # The head process should write its stdout to a pipe.
            redir = process.StdoutToPipe(r,
                                         w)  # type: process.ChildStateChange

        elif op_id == Id.Left_ProcSubOut:
            # Example: head foo.txt > >(tac)
            #
            # The tac process should read its stdin from a pipe.

            # Note: this example sometimes requires you to hit "enter" in bash and
            # zsh.  WHy?
            redir = process.StdinFromPipe(r, w)

        else:
            raise AssertionError()

        p.AddStateChange(redir)

        if self.job_control.Enabled():
            p.AddStateChange(process.SetPgid(process.OWN_LEADER, self.tracer))

        # Fork, letting the child inherit the pipe file descriptors.
        p.StartProcess(trace.ProcessSub)

        ps_frame = self.process_sub_stack[-1]

        # Note: bash never waits() on the process, but zsh does.  The calling
        # program needs to read() before we can wait, e.g.
        #   diff <(sort left.txt) <(sort right.txt)

        # After forking, close the end of the pipe we're not using.
        if op_id == Id.Left_ProcSubIn:
            posix.close(w)  # cat < <(head foo.txt)
            ps_frame.Append(p, r, cs_loc)  # close later
        elif op_id == Id.Left_ProcSubOut:
            posix.close(r)
            #log('Left_ProcSubOut closed %d', r)
            ps_frame.Append(p, w, cs_loc)  # close later
        else:
            raise AssertionError()

        # Is /dev Linux-specific?
        if op_id == Id.Left_ProcSubIn:
            return '/dev/fd/%d' % r

        elif op_id == Id.Left_ProcSubOut:
            return '/dev/fd/%d' % w

        else:
            raise AssertionError()

    def PushRedirects(self, redirects, err_out):
        # type: (List[RedirValue], List[error.IOError_OSError]) -> None
        if len(redirects) == 0:  # Optimized to avoid allocs
            return
        self.fd_state.Push(redirects, err_out)

    def PopRedirects(self, num_redirects, err_out):
        # type: (int, List[error.IOError_OSError]) -> None
        if num_redirects == 0:  # Optimized to avoid allocs
            return
        self.fd_state.Pop(err_out)

    def PushProcessSub(self):
        # type: () -> None
        if len(self.clean_frame_pool):
            # Optimized to avoid allocs
            new_frame = self.clean_frame_pool.pop()
        else:
            new_frame = _ProcessSubFrame()
        self.process_sub_stack.append(new_frame)

    def PopProcessSub(self, compound_st):
        # type: (StatusArray) -> None
        """This method is called by a context manager, which means we always
        wait() on the way out, which I think is the right thing.

        We don't always set _process_sub_status, e.g. if some fatal
        error occurs first, but we always wait.
        """
        frame = self.process_sub_stack.pop()
        if frame.WasModified():
            frame.MaybeWaitOnProcessSubs(self.waiter, compound_st)
        else:
            # Optimized to avoid allocs
            self.clean_frame_pool.append(frame)

        # Note: the 3 lists in _ProcessSubFrame are hot in our profiles.  It would
        # be nice to somehow "destroy" them here, rather than letting them become
        # garbage that needs to be traced.

        # The CommandEvaluator could have a ProcessSubStack, which supports Push(),
        # Pop(), and Top() of VALUES rather than GC objects?
