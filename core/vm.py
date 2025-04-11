"""vm.py: Library for executing shell."""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Id_t, Id_str
from _devbuild.gen.runtime_asdl import (CommandStatus, StatusArray, flow_e,
                                        flow_t)
from _devbuild.gen.syntax_asdl import Token, loc, loc_t
from _devbuild.gen.value_asdl import value, value_e, value_t, Obj
from core import dev
from core import error
from core.error import e_die
from core import pyos
from core import pyutil
from display import ui
from mycpp.mylib import log, tagswitch

from typing import List, Dict, Tuple, Optional, Any, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value, RedirValue
    from _devbuild.gen.syntax_asdl import (command, command_t, CommandSub)
    from builtin import hay_ysh
    from core import optview
    from core import state
    from frontend import typed_args
    from osh import sh_expr_eval
    from osh.sh_expr_eval import ArithEvaluator
    from osh.sh_expr_eval import BoolEvaluator
    from osh import word_eval
    from osh import cmd_eval
    from osh import prompt
    from ysh import expr_eval

_ = log


class ControlFlow(Exception):
    """Internal exception for control flow.

    Used by CommandEvaluator and 'source' builtin

    break and continue are caught by loops, return is caught by functions.
    """
    pass


class IntControlFlow(Exception):

    def __init__(self, keyword_id, keyword_str, keyword_loc, arg):
        # type: (Id_t, str, loc_t, int) -> None
        """
        Args:
          token: the keyword token
          arg: exit code to 'return', or number of levels to break/continue
        """
        self.keyword_id = keyword_id
        self.keyword_str = keyword_str
        self.keyword_loc = keyword_loc
        self.arg = arg

    def Keyword(self):
        # type: () -> str
        return self.keyword_str

    def Location(self):
        # type: () -> loc_t
        return self.keyword_loc

    def IsReturn(self):
        # type: () -> bool
        return self.keyword_id == Id.ControlFlow_Return

    def IsBreak(self):
        # type: () -> bool
        return self.keyword_id == Id.ControlFlow_Break

    def IsContinue(self):
        # type: () -> bool
        return self.keyword_id == Id.ControlFlow_Continue

    def StatusCode(self):
        # type: () -> int
        assert self.IsReturn()
        # All shells except dash do this truncation.
        # turn 257 into 1, and -1 into 255.
        return self.arg & 0xff

    def HandleLoop(self):
        # type: () -> flow_t
        """Mutates this exception and returns what the caller should do."""

        if self.IsBreak():
            self.arg -= 1
            if self.arg == 0:
                return flow_e.Break  # caller should break out of loop

        elif self.IsContinue():
            self.arg -= 1
            if self.arg == 0:
                return flow_e.Nothing  # do nothing to continue

        # return / break 2 / continue 2 need to pop up more
        return flow_e.Raise

    def __repr__(self):
        # type: () -> str
        return '<IntControlFlow %s %s>' % (Id_str(self.keyword_id), self.arg)


class ValueControlFlow(Exception):

    def __init__(self, token, value):
        # type: (Token, value_t) -> None
        """
        Args:
          token: the keyword token
          value: value_t to 'return' from a function
        """
        self.token = token
        self.value = value

    def __repr__(self):
        # type: () -> str
        return '<ValueControlFlow %s %s>' % (self.token, self.value)


def InitUnsafeArith(mem, word_ev, unsafe_arith):
    # type: (state.Mem, word_eval.NormalWordEvaluator, sh_expr_eval.UnsafeArith) -> None
    """Wire up circular dependencies for UnsafeArith."""
    mem.unsafe_arith = unsafe_arith  # for 'declare -n' nameref expansion of a[i]
    word_ev.unsafe_arith = unsafe_arith  # for ${!ref} expansion of a[i]


def InitCircularDeps(
        arith_ev,  # type: ArithEvaluator
        bool_ev,  # type: BoolEvaluator
        expr_ev,  # type: expr_eval.ExprEvaluator
        word_ev,  # type: word_eval.NormalWordEvaluator
        cmd_ev,  # type: cmd_eval.CommandEvaluator
        shell_ex,  # type: _Executor
        pure_ex,  # type: _Executor
        prompt_ev,  # type: prompt.Evaluator
        global_io,  # type: Obj
        tracer,  # type: dev.Tracer
):
    # type: (...) -> None
    """Wire up mutually recursive evaluators and runtime objects."""
    arith_ev.word_ev = word_ev
    bool_ev.word_ev = word_ev

    if expr_ev:  # for pure OSH
        expr_ev.shell_ex = shell_ex
        expr_ev.cmd_ev = cmd_ev
        expr_ev.word_ev = word_ev

    word_ev.arith_ev = arith_ev
    word_ev.expr_ev = expr_ev
    word_ev.prompt_ev = prompt_ev
    word_ev.shell_ex = shell_ex

    cmd_ev.shell_ex = shell_ex
    cmd_ev.arith_ev = arith_ev
    cmd_ev.bool_ev = bool_ev
    cmd_ev.expr_ev = expr_ev
    cmd_ev.word_ev = word_ev
    cmd_ev.tracer = tracer

    shell_ex.cmd_ev = cmd_ev
    pure_ex.cmd_ev = cmd_ev

    prompt_ev.word_ev = word_ev
    prompt_ev.expr_ev = expr_ev
    prompt_ev.global_io = global_io

    tracer.word_ev = word_ev

    arith_ev.CheckCircularDeps()
    bool_ev.CheckCircularDeps()
    if expr_ev:
        expr_ev.CheckCircularDeps()
    word_ev.CheckCircularDeps()
    cmd_ev.CheckCircularDeps()
    shell_ex.CheckCircularDeps()
    pure_ex.CheckCircularDeps()
    prompt_ev.CheckCircularDeps()
    tracer.CheckCircularDeps()


class _Executor(object):

    def __init__(
            self,
            mem,  # type: state.Mem
            exec_opts,  # type: optview.Exec
            mutable_opts,  # type: state.MutableOpts
            procs,  # type: state.Procs
            hay_state,  # type: hay_ysh.HayState
            builtins,  # type: Dict[int, _Builtin]
            tracer,  # type: dev.Tracer
            errfmt  # type: ui.ErrorFormatter
    ):
        self.mem = mem
        self.exec_opts = exec_opts
        self.mutable_opts = mutable_opts  # for IsDisabled(), not mutating
        self.procs = procs
        self.hay_state = hay_state
        self.builtins = builtins
        self.tracer = tracer
        self.errfmt = errfmt

        # Not a constructor argument
        self.cmd_ev = None  # type: cmd_eval.CommandEvaluator

    def CheckCircularDeps(self):
        # type: () -> None
        assert self.cmd_ev is not None

    def RunSimpleCommand(self, cmd_val, cmd_st, run_flags):
        # type: (cmd_value.Argv, CommandStatus, int) -> int
        """Shared between ShellExecutor and PureExecutor"""
        if len(cmd_val.arg_locs):
            arg0_loc = cmd_val.arg_locs[0]  # type: loc_t
        else:
            arg0_loc = loc.Missing

        argv = cmd_val.argv
        # This happens when you write "$@" but have no arguments.
        if len(argv) == 0:
            if self.exec_opts.strict_argv():
                e_die("Command evaluated to an empty argv array", arg0_loc)
            else:
                return 0  # do nothing

        return self._RunSimpleCommand(argv[0], arg0_loc, cmd_val, cmd_st,
                                      run_flags)

    def _RunSimpleCommand(self, arg0, arg0_loc, cmd_val, cmd_st, run_flags):
        # type: (str, loc_t, cmd_value.Argv, CommandStatus, int) -> int
        raise NotImplementedError()

    def RunBuiltin(self, builtin_id, cmd_val):
        # type: (int, cmd_value.Argv) -> int
        """Run a builtin.

        Also called by the 'builtin' builtin, in builtin/meta_oils.py
        """
        self.tracer.OnBuiltin(builtin_id, cmd_val.argv)

        builtin_proc = self.builtins[builtin_id]

        return self._RunBuiltinProc(builtin_proc, cmd_val)

    def _RunBuiltinProc(self, builtin_proc, cmd_val):
        # type: (_Builtin, cmd_value.Argv) -> int

        io_errors = []  # type: List[error.IOError_OSError]
        with ctx_FlushStdout(io_errors):
            # note: could be second word, like 'builtin read'
            with ui.ctx_Location(self.errfmt, cmd_val.arg_locs[0]):
                try:
                    status = builtin_proc.Run(cmd_val)
                    assert isinstance(status, int)
                except (IOError, OSError) as e:
                    self.errfmt.PrintMessage(
                        '%s builtin I/O error: %s' %
                        (cmd_val.argv[0], pyutil.strerror(e)),
                        cmd_val.arg_locs[0])
                    return 1
                except error.Usage as e:
                    arg0 = cmd_val.argv[0]
                    # e.g. 'type' doesn't accept flag '-x'
                    self.errfmt.PrefixPrint(e.msg, '%r ' % arg0, e.location)
                    return 2  # consistent error code for usage error

        if len(io_errors):  # e.g. disk full, ulimit
            self.errfmt.PrintMessage(
                '%s builtin I/O error: %s' %
                (cmd_val.argv[0], pyutil.strerror(io_errors[0])),
                cmd_val.arg_locs[0])
            return 1

        return status

    def _RunInvokable(self, proc_val, self_obj, arg0_loc, cmd_val):
        # type: (value_t, Optional[Obj], loc_t, cmd_value.Argv) -> int

        cmd_val.self_obj = self_obj  # MAYBE bind self

        if self.exec_opts.strict_errexit():
            disabled_tok = self.mutable_opts.ErrExitDisabledToken()
            if disabled_tok:
                self.errfmt.Print_('errexit was disabled for this construct',
                                   disabled_tok)
                self.errfmt.StderrLine('')
                e_die(
                    "Can't run a proc while errexit is disabled. "
                    "Use 'try' or wrap it in a process with $0 myproc",
                    arg0_loc)

        with tagswitch(proc_val) as case:
            if case(value_e.BuiltinProc):
                # Handle the special case of the BUILTIN proc
                # module_ysh.ModuleInvoke, which is returned on the Obj
                # created by 'use util.ysh'
                builtin_proc = cast(value.BuiltinProc, proc_val)
                b = cast(_Builtin, builtin_proc.builtin)
                status = self._RunBuiltinProc(b, cmd_val)

            elif case(value_e.Proc):
                proc = cast(value.Proc, proc_val)
                with dev.ctx_Tracer(self.tracer, 'proc', cmd_val.argv):
                    # NOTE: Functions could call 'exit 42' directly, etc.
                    status = self.cmd_ev.RunProc(proc, cmd_val)

            else:
                # GetInvokable() should only return 1 of 2 things
                raise AssertionError()

        return status

    def RunBackgroundJob(self, node):
        # type: (command_t) -> int
        return 0

    def RunPipeline(self, node, status_out):
        # type: (command.Pipeline, CommandStatus) -> None
        pass

    def RunSubshell(self, node):
        # type: (command_t) -> int
        return 0

    def CaptureStdout(self, node):
        # type: (command_t) -> Tuple[int, str]
        return 0, ''

    def CaptureOutputs(self, node):
        # type: (command_t) -> Tuple[int, str, str]
        return 0, '', ''

    def RunCommandSub(self, cs_part):
        # type: (CommandSub) -> str
        return ''

    def RunProcessSub(self, cs_part):
        # type: (CommandSub) -> str
        return ''

    def PushRedirects(self, redirects, err_out):
        # type: (List[RedirValue], List[error.IOError_OSError]) -> None
        pass

    def PopRedirects(self, num_redirects, err_out):
        # type: (int, List[error.IOError_OSError]) -> None
        pass

    def PushProcessSub(self):
        # type: () -> None
        pass

    def PopProcessSub(self, compound_st):
        # type: (StatusArray) -> None
        pass


#
# Abstract base classes
#


class _AssignBuiltin(object):
    """Interface for assignment builtins."""

    def __init__(self):
        # type: () -> None
        """Empty constructor for mycpp."""
        pass

    def Run(self, cmd_val):
        # type: (cmd_value.Assign) -> int
        raise NotImplementedError()


class _Builtin(object):
    """All builtins except 'command' obey this interface.

    Assignment builtins use cmd_value.Assign; others use cmd_value.Argv.
    """

    def __init__(self):
        # type: () -> None
        """Empty constructor for mycpp."""
        pass

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        raise NotImplementedError()


class _Callable(object):
    """Interface for functions in the runtime."""

    def __init__(self):
        # type: () -> None
        """Empty constructor for mycpp."""
        pass

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t
        raise NotImplementedError()


class ctx_MaybePure(object):
    """Enforce purity of the shell interpreter

    Use this for:

      --eval-pure
      func - pure functions
      eval() evalToDict() - builtin pure functions, not methods
    """

    def __init__(
            self,
            pure_ex,  # type: Optional[_Executor]
            cmd_ev,  # type: cmd_eval.CommandEvaluator
    ):
        # type: (...) -> None
        self.pure_ex = pure_ex
        if not pure_ex:
            return  # do nothing

        word_ev = cmd_ev.word_ev
        expr_ev = cmd_ev.expr_ev

        # Save the Shell Executor
        self.saved = cmd_ev.shell_ex
        assert self.saved is word_ev.shell_ex
        assert self.saved is expr_ev.shell_ex

        # Patch evaluators to use the Pure Executor
        cmd_ev.shell_ex = pure_ex
        word_ev.shell_ex = pure_ex
        expr_ev.shell_ex = pure_ex

        self.cmd_ev = cmd_ev

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        if not self.pure_ex:
            return  # do nothing

        # Unpatch the evaluators
        self.cmd_ev.shell_ex = self.saved
        self.cmd_ev.word_ev.shell_ex = self.saved
        self.cmd_ev.expr_ev.shell_ex = self.saved


class ctx_Redirect(object):
    """For closing files.

    This is asymmetric because if PushRedirects fails, then we don't execute
    the command at all.

    Example:
      { seq 3 > foo.txt; echo 4; } > bar.txt
    """

    def __init__(self, shell_ex, num_redirects, err_out):
        # type: (_Executor, int, List[error.IOError_OSError]) -> None
        self.shell_ex = shell_ex
        self.num_redirects = num_redirects
        self.err_out = err_out

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.shell_ex.PopRedirects(self.num_redirects, self.err_out)


class ctx_ProcessSub(object):
    """For waiting on processes started during word evaluation.

    Example:
      diff <(seq 3) <(seq 4) > >(tac)
    """

    def __init__(self, shell_ex, process_sub_status):
        # type: (_Executor, StatusArray) -> None
        shell_ex.PushProcessSub()
        self.shell_ex = shell_ex
        self.process_sub_status = process_sub_status

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None

        # Wait and return array to set _process_sub_status
        self.shell_ex.PopProcessSub(self.process_sub_status)


class ctx_FlushStdout(object):

    def __init__(self, err_out):
        # type: (List[error.IOError_OSError]) -> None
        self.err_out = err_out

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None

        # Can't raise exception in destructor!  So we append it to out param.
        err = pyos.FlushStdout()
        if err is not None:
            self.err_out.append(err)
