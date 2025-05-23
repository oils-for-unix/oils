"""Methods on Obj that is the io type"""
from __future__ import print_function

from _devbuild.gen.value_asdl import value, value_e, value_t
from _devbuild.gen.syntax_asdl import loc_t

from core import error
from core import num
from core import state
from core import vm
from frontend import typed_args
from mycpp.mylib import log, NewDict
from osh import prompt

from typing import Dict, List, Optional, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import Cell
    from osh import cmd_eval
    from ysh import expr_eval

_ = log

EVAL_NULL = 1
EVAL_DICT = 2


def _CheckPosArgs(pos_args_raw, blame_loc):
    # type: (Optional[List[value_t]], loc_t) -> Optional[List[str]]

    if pos_args_raw is None:
        return None

    pos_args = []  # type: List[str]
    for arg in pos_args_raw:
        if arg.tag() != value_e.Str:
            raise error.TypeErr(arg, "Expected pos_args to be a List of Strs",
                                blame_loc)

        pos_args.append(cast(value.Str, arg).s)
    return pos_args


class EvalExpr(vm._Callable):
    """io->evalExpr(ex) evaluates an expression 

    Notes compared with io->eval(cmd):
    - there is no to_dict=true variant - doesn't make sense
    - Does it need in_captured_frame=true?
      - That is for "inline procs" like cd, but doesn't seem to be necessary
        for expressions.  Unless we had mutations in expressions.
    """

    def __init__(
            self,
            expr_ev,  # type: expr_eval.ExprEvaluator
            pure_ex,  # type: Optional[vm._Executor]
            cmd_ev,  # type: Optional[cmd_eval.CommandEvaluator]
    ):
        # type: (...) -> None
        self.expr_ev = expr_ev
        self.pure_ex = pure_ex
        self.cmd_ev = cmd_ev
        self.mem = expr_ev.mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        if self.pure_ex is None:
            unused_self = rd.PosObj()
        lazy = rd.PosExpr()

        dollar0 = rd.NamedStr("dollar0", None)
        pos_args_raw = rd.NamedList("pos_args", None)
        vars_ = rd.NamedDict("vars", None)
        rd.Done()

        blame_tok = rd.LeftParenToken()
        pos_args = _CheckPosArgs(pos_args_raw, blame_tok)

        # Note: ctx_Eval is on the outside, while ctx_EnclosedFrame is used in
        # EvalExprClosure
        with state.ctx_TokenDebugFrame(self.mem, blame_tok):
            with state.ctx_EnclosedFrame(self.mem, lazy.captured_frame,
                                         lazy.module_frame, None):
                with state.ctx_Eval(self.mem, dollar0, pos_args, vars_):
                    with vm.ctx_MaybePure(self.pure_ex, self.cmd_ev):
                        result = self.expr_ev.EvalExpr(lazy.e, blame_tok)

        return result


if 0:

    def _PrintFrame(prefix, frame):
        # type: (str, Dict[str, Cell]) -> None
        print('%s %s' % (prefix, ' '.join(frame.keys())))

        rear = frame.get('__E__')
        if rear:
            rear_val = rear.val
            if rear_val.tag() == value_e.Frame:
                r = cast(value.Frame, rear_val)
                _PrintFrame('--> ' + prefix, r.frame)


class EvalInFrame(vm._Callable):
    """
    DEPRECATED, replaced by eval(b, in_captured_frame=true)
    """

    def __init__(self, mem, cmd_ev):
        # type: (state.Mem, cmd_eval.CommandEvaluator) -> None
        self.mem = mem
        self.cmd_ev = cmd_ev

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        unused = rd.PosValue()

        cmd = rd.PosCommand()
        in_frame = rd.PosFrame()
        rd.Done()

        frag = typed_args.GetCommandFrag(cmd)

        # Note that 'cd' uses cmd_ev.EvalCommandFrag(), because a builtin does
        # NOT push a new stack frame.  But a proc does.  So we need
        # evalInFrame().

        with state.ctx_TokenDebugFrame(self.mem, rd.LeftParenToken()):
            # Evaluate with the given frame at the TOP of the stack
            with state.ctx_EvalInFrame(self.mem, in_frame):
                unused_status = self.cmd_ev.EvalCommandFrag(frag)

        return value.Null


class Eval(vm._Callable):
    """
    These are similar:

        var cmd = ^(echo hi)
        call io->eval(cmd)

    Also give the top namespace

        call io->evalToDict(cmd)

    The CALLER must handle errors.
    """

    def __init__(self, mem, cmd_ev, pure_ex, which):
        # type: (state.Mem, cmd_eval.CommandEvaluator, Optional[vm._Executor], int) -> None
        self.mem = mem
        self.cmd_ev = cmd_ev
        self.pure_ex = pure_ex
        self.which = which

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        if self.pure_ex is None:
            unused = rd.PosValue()
        bound = rd.PosCommand()

        dollar0 = rd.NamedStr("dollar0", None)
        pos_args_raw = rd.NamedList("pos_args", None)
        vars_ = rd.NamedDict("vars", None)
        in_captured_frame = rd.NamedBool("in_captured_frame", False)
        to_dict = rd.NamedBool("to_dict", False)
        rd.Done()

        frag = typed_args.GetCommandFrag(bound)

        pos_args = _CheckPosArgs(pos_args_raw, rd.LeftParenToken())

        with state.ctx_TokenDebugFrame(self.mem, rd.LeftParenToken()):
            if self.which == EVAL_NULL:
                if to_dict:
                    bindings = NewDict()  # type: Optional[Dict[str, value_t]]
                else:
                    bindings = None
            elif self.which == EVAL_DICT:  # TODO: remove evalToDict()
                bindings = NewDict()
            else:
                raise AssertionError()

            # _PrintFrame('[captured]', captured_frame)
            with state.ctx_EnclosedFrame(self.mem,
                                         bound.captured_frame,
                                         bound.module_frame,
                                         bindings,
                                         inside=in_captured_frame):
                # _PrintFrame('[new]', self.cmd_ev.mem.var_stack[-1])
                with state.ctx_Eval(self.mem, dollar0, pos_args, vars_):
                    with vm.ctx_MaybePure(self.pure_ex, self.cmd_ev):
                        unused_status = self.cmd_ev.EvalCommandFrag(frag)

            if bindings is not None:
                return value.Dict(bindings)
            else:
                return value.Null


class CaptureStdout(vm._Callable):

    def __init__(self, mem, shell_ex):
        # type: (state.Mem, vm._Executor) -> None
        self.mem = mem
        self.shell_ex = shell_ex

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        unused = rd.PosValue()
        cmd = rd.PosCommand()
        rd.Done()  # no more args

        frag = typed_args.GetCommandFrag(cmd)
        with state.ctx_EnclosedFrame(self.mem, cmd.captured_frame,
                                     cmd.module_frame, None):
            status, stdout_str = self.shell_ex.CaptureStdout(frag)
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


class CaptureAll(vm._Callable):
    def __init__(self, mem, shell_ex):
        # type: (state.Mem, vm._Executor) -> None
        self.mem = mem
        self.shell_ex = shell_ex

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        unused = rd.PosValue()
        cmd = rd.PosCommand()
        rd.Done()  # no more args
        frag = typed_args.GetCommandFrag(cmd)
        with state.ctx_EnclosedFrame(self.mem, cmd.captured_frame,
                                     cmd.module_frame, None):
            status, stdout_str, stderr_str = self.shell_ex.Capture3(frag)

        out = NewDict() # type: Dict[str, value_t]
        out['stdout'] = value.Str(stdout_str)
        out['stderr'] = value.Str(stderr_str)
        out['status'] = num.ToBig(status)

        return value.Dict(out)

class PromptVal(vm._Callable):
    """
    _io->promptVal('$') is like \$ 
    It expands to $ or # when root
    """

    def __init__(self, prompt_ev):
        # type: (prompt.Evaluator) -> None
        self.prompt_ev = prompt_ev

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        # "self" param is guaranteed to succeed
        unused = rd.PosValue()
        what = rd.PosStr()
        rd.Done()  # no more args

        # Bug fix: protect against crash later in PromptVal()
        if len(what) != 1:
            raise error.Expr(
                'promptVal() expected a single char, got %r' % what,
                rd.LeftParenToken())

        return value.Str(self.prompt_ev.PromptVal(what))


# TODO: Implement these


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


class Glob(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        return value.Null
