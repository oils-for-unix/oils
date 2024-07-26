from __future__ import print_function

from _devbuild.gen.option_asdl import option_i
from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import cmd_value, CommandStatus
from _devbuild.gen.syntax_asdl import loc, loc_t, expr, expr_e
from _devbuild.gen.value_asdl import value, value_e
from core import error
from core.error import e_die_status, e_usage
from core import executor
from core import num
from core import state
from core import vm
from data_lang import j8
from frontend import flag_util
from frontend import typed_args
from mycpp import mops
from mycpp.mylib import tagswitch, log
from ysh import val_ops

_ = log

from typing import Any, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from core import ui
    from osh import cmd_eval
    from ysh import expr_eval


class ctx_Try(object):

    def __init__(self, mutable_opts):
        # type: (state.MutableOpts) -> None

        mutable_opts.Push(option_i.errexit, True)
        self.mutable_opts = mutable_opts

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mutable_opts.Pop(option_i.errexit)


class Try(vm._Builtin):
    """Allows explicit handling of errors.

    Takes command argv, or a block:

    try ls /bad

    try {
      var x = 1 / 0

      ls | wc -l

      diff <(sort left.txt) <(sort right.txt)
    }

    TODO:
    - Set _error_str (e.UserErrorString())
    - Set _error_location
    - These could be used by a 'raise' builtin?  Or 'reraise'

    try {
      foo
    }
    if (_status !== 0) {
      echo 'hello'
      raise  # reads _status, _error_str, and _error_location ?
    }
    """

    def __init__(
            self,
            mutable_opts,  # type: state.MutableOpts
            mem,  # type: state.Mem
            cmd_ev,  # type: cmd_eval.CommandEvaluator
            shell_ex,  # type: vm._Executor
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        self.mutable_opts = mutable_opts
        self.mem = mem
        self.shell_ex = shell_ex
        self.cmd_ev = cmd_ev
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('try_',
                                         cmd_val,
                                         accept_typed_args=True)

        rd = typed_args.ReaderForProc(cmd_val)
        cmd = rd.RequiredBlock()
        rd.Done()

        error_dict = None  # type: value.Dict

        status = 0  # success by default
        try:
            with ctx_Try(self.mutable_opts):
                unused = self.cmd_ev.EvalCommand(cmd)
        except error.Expr as e:
            status = e.ExitStatus()
        except error.ErrExit as e:
            status = e.ExitStatus()

        except error.Structured as e:
            #log('*** STRUC %s', e)
            status = e.ExitStatus()
            error_dict = e.ToDict()

        if error_dict is None:
            error_dict = value.Dict({'code': num.ToBig(status)})

        # Always set _error
        self.mem.SetTryError(error_dict)

        # TODO: remove _status in favor of _error.code.  This is marked in
        # spec/TODO-deprecate
        self.mem.SetTryStatus(status)
        return 0


class Failed(vm._Builtin):

    def __init__(self, mem):
        # type: (state.Mem) -> None
        self.mem = mem

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('failed', cmd_val)

        # No args
        arg_r.Done()

        # Should we have
        #   failed (_error) ?

        err = self.mem.TryError()
        code = err.d.get('code')
        if code is None:
            # No error
            return 1

        UP_code = code
        with tagswitch(code) as case:
            if case(value_e.Int):
                code = cast(value.Int, UP_code)
                # return 0 if and only if it failed
                return 1 if mops.Equal(code.i, mops.ZERO) else 0
            else:
                # This should never happen because the interpreter controls the
                # contents of TryError()
                raise AssertionError()


class Error(vm._Builtin):

    def __init__(self):
        # type: () -> None
        pass

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('error',
                                         cmd_val,
                                         accept_typed_args=True)

        message = arg_r.Peek()
        if message is None:
            raise error.Usage('expected a message to display',
                              cmd_val.arg_locs[0])

        rd = typed_args.ReaderForProc(cmd_val)
        # Status 10 is distinct from what the Oils interpreter itself uses.  We
        # use status 3 for expressions and 4 for encode/decode, and 10 "leaves
        # room" for others.
        # The user is of course free to choose status 1.
        status = mops.BigTruncate(rd.NamedInt('code', 10))

        # attach rest of named args to _error Dict
        properties = rd.RestNamed()
        rd.Done()

        if status == 0:
            raise error.Usage('status must be a non-zero integer',
                              cmd_val.arg_locs[0])

        raise error.Structured(status, message, cmd_val.arg_locs[0],
                               properties)


class BoolStatus(vm._Builtin):

    def __init__(self, shell_ex, errfmt):
        # type: (vm._Executor, ui.ErrorFormatter) -> None
        self.shell_ex = shell_ex
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        _, arg_r = flag_util.ParseCmdVal('boolstatus', cmd_val)

        if arg_r.Peek() is None:
            e_usage('expected a command to run', loc.Missing)

        argv, locs = arg_r.Rest2()
        cmd_val2 = cmd_value.Argv(argv, locs, cmd_val.typed_args,
                                  cmd_val.pos_args, cmd_val.named_args,
                                  cmd_val.block_arg)

        cmd_st = CommandStatus.CreateNull(alloc_lists=True)
        status = self.shell_ex.RunSimpleCommand(cmd_val2, cmd_st,
                                                executor.DO_FORK)

        if status not in (0, 1):
            e_die_status(status,
                         'boolstatus expected status 0 or 1, got %d' % status,
                         locs[0])

        return status


class Assert(vm._Builtin):

    def __init__(self, expr_ev, errfmt):
        # type: (expr_eval.ExprEvaluator, ui.ErrorFormatter) -> None
        self.expr_ev = expr_ev
        self.errfmt = errfmt

    def _AssertComparison(self, exp, blame_loc):
        # type: (expr.Compare, loc_t) -> None

        # We checked exp.ops
        assert len(exp.comparators) == 1, exp.comparators

        expected = self.expr_ev.EvalExpr(exp.left, loc.Missing)
        actual = self.expr_ev.EvalExpr(exp.comparators[0], loc.Missing)

        if not val_ops.ExactlyEqual(expected, actual, blame_loc):
            self.errfmt.StderrLine('')
            self.errfmt.StderrLine('  Expected: %s' % j8.Repr(expected))
            self.errfmt.StderrLine('  Got:      %s' % j8.Repr(actual))

            raise error.Expr("Not equal", exp.ops[0])

    def _AssertExpression(self, val, blame_loc):
        # type: (value.Expr, loc_t) -> None

        # Special case for assert [true === f()]
        exp = val.e
        UP_exp = exp
        with tagswitch(exp) as case:
            if case(expr_e.Compare):
                exp = cast(expr.Compare, UP_exp)

                # Only assert [x === y] is treated as special
                # Not  assert [x === y === z]
                if len(exp.ops) == 1:
                    id_ = exp.ops[0].id
                    if id_ == Id.Expr_TEqual:
                        self._AssertComparison(exp, blame_loc)
                        return

        # Any other expression
        result = self.expr_ev.EvalExpr(val.e, blame_loc)
        b = val_ops.ToBool(result)
        if not b:
            s = j8.Repr(result)
            raise error.Expr('Assertion (of expr) %s' % s, blame_loc)

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        _, arg_r = flag_util.ParseCmdVal('assert',
                                         cmd_val,
                                         accept_typed_args=True)

        rd = typed_args.ReaderForProc(cmd_val)
        val = rd.PosValue()
        rd.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.Expr):  # Destructured assert [true === f()]
                val = cast(value.Expr, UP_val)
                self._AssertExpression(val, rd.LeftParenToken())
            else:
                b = val_ops.ToBool(val)
                if not b:
                    raise error.Expr('Assert: %s' % j8.Repr(val),
                                     rd.LeftParenToken())

        return 0
