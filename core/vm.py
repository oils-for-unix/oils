"""vm.py: Library for executing shell."""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import (CommandStatus, StatusArray, flow_e,
                                        flow_t)
from _devbuild.gen.syntax_asdl import Token
from _devbuild.gen.value_asdl import value_t, Obj
from core import error
from core import pyos
from mycpp.mylib import log

from typing import List, Tuple, Any, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value, RedirValue
    from _devbuild.gen.syntax_asdl import (command, command_t, CommandSub)
    from frontend import typed_args
    from osh import sh_expr_eval
    from osh.sh_expr_eval import ArithEvaluator
    from osh.sh_expr_eval import BoolEvaluator
    from ysh.expr_eval import ExprEvaluator
    from osh.word_eval import NormalWordEvaluator
    from osh.cmd_eval import CommandEvaluator
    from osh import prompt
    from core import dev
    from core import state

_ = log


class ControlFlow(Exception):
    """Internal exception for control flow.

    Used by CommandEvaluator and 'source' builtin

    break and continue are caught by loops, return is caught by functions.
    """
    pass


class IntControlFlow(Exception):

    def __init__(self, token, arg):
        # type: (Token, int) -> None
        """
        Args:
          token: the keyword token
          arg: exit code to 'return', or number of levels to break/continue
        """
        self.token = token
        self.arg = arg

    def IsReturn(self):
        # type: () -> bool
        return self.token.id == Id.ControlFlow_Return

    def IsBreak(self):
        # type: () -> bool
        return self.token.id == Id.ControlFlow_Break

    def IsContinue(self):
        # type: () -> bool
        return self.token.id == Id.ControlFlow_Continue

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
        return '<IntControlFlow %s %s>' % (self.token, self.arg)


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
    # type: (state.Mem, NormalWordEvaluator, sh_expr_eval.UnsafeArith) -> None
    """Wire up circular dependencies for UnsafeArith."""
    mem.unsafe_arith = unsafe_arith  # for 'declare -n' nameref expansion of a[i]
    word_ev.unsafe_arith = unsafe_arith  # for ${!ref} expansion of a[i]


def InitCircularDeps(
        arith_ev,  # type: ArithEvaluator
        bool_ev,  # type: BoolEvaluator
        expr_ev,  # type: ExprEvaluator
        word_ev,  # type: NormalWordEvaluator
        cmd_ev,  # type: CommandEvaluator
        shell_ex,  # type:  _Executor
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
    prompt_ev.CheckCircularDeps()
    tracer.CheckCircularDeps()


class _Executor(object):

    def __init__(self):
        # type: () -> None
        self.cmd_ev = None  # type: CommandEvaluator

    def CheckCircularDeps(self):
        # type: () -> None
        pass

    def RunBuiltin(self, builtin_id, cmd_val):
        # type: (int, cmd_value.Argv) -> int
        """The 'builtin' builtin in osh/builtin_meta.py needs this."""
        return 0

    def RunSimpleCommand(self, cmd_val, cmd_st, run_flags):
        # type: (cmd_value.Argv, CommandStatus, int) -> int
        return 0

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
