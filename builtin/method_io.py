"""Methods on IO type"""
from __future__ import print_function

from _devbuild.gen.value_asdl import value, value_t

from core import error
from core import num
from core import vm
from mycpp.mylib import log
from osh import prompt

from typing import Dict, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from frontend import typed_args
    from osh import cmd_eval

_ = log


class Eval(vm._Callable):
    """
    These are similar:

        var c = ^(echo hi)

        eval (c)
        call _io->eval(c)

    The CALLER must handle errors.
    """
    def __init__(self, cmd_ev):
        # type: (cmd_eval.CommandEvaluator) -> None
        self.cmd_ev = cmd_ev

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        io = rd.PosIO()
        cmd = rd.PosCommand()
        rd.Done()  # no more args

        # errors can arise from false' and 'exit'
        unused_status = self.cmd_ev.EvalCommand(cmd)
        return value.Null


class CaptureStdout(vm._Callable):

    def __init__(self, shell_ex):
        # type: (vm._Executor) -> None
        self.shell_ex = shell_ex

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        io = rd.PosIO()
        cmd = rd.PosCommand()
        rd.Done()  # no more args

        status, stdout_str = self.shell_ex.CaptureStdout(cmd)
        if status != 0:
            # Note that $() raises error.ErrExit with the status.
            # But I think that results in a more confusing error message, so we
            # "wrap" the errors.
            properties = {
                'status': num.ToBig(status)
            }  # type: Dict[str, value_t]
            raise error.Structured(
                4, 'captureStdout(): command failed with status %d' % status,
                rd.LeftParenToken(), properties)

        return value.Str(stdout_str)


class PromptVal(vm._Callable):
    """
    _io->promptVal('$') is like \$ 
    It expands to $ or # when root
    """

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        # "self" param is guaranteed to succeed
        io = rd.PosIO()
        what = rd.PosStr()
        rd.Done()  # no more args

        # Bug fix: protect against crash later in PromptVal()
        if len(what) != 1:
            raise error.Expr(
                'promptVal() expected a single char, got %r' % what,
                rd.LeftParenToken())

        prompt_ev = cast(prompt.Evaluator, io.prompt_ev)
        return value.Str(prompt_ev.PromptVal(what))


class Time(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        return value.Null


class Strftime(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        return value.Null
