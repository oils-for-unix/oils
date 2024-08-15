#!/usr/bin/env python2
"""
User-defined funcs and procs
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import cmd_value, ProcArgs
from _devbuild.gen.syntax_asdl import (proc_sig, proc_sig_e, Param, ParamGroup,
                                       NamedArg, Func, loc, ArgList, expr,
                                       expr_e, expr_t)
from _devbuild.gen.value_asdl import (value, value_e, value_t, ProcDefaults,
                                      LeftName)

from core import error
from core.error import e_die
from core import state
from core import vm
from frontend import lexer
from frontend import typed_args
from mycpp import mylib
from mycpp.mylib import log, NewDict

from typing import List, Tuple, Dict, Optional, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import command, loc_t
    from osh import cmd_eval
    from ysh import expr_eval

_ = log

# TODO:
# - use _EvalExpr more?
#   - a single with state.ctx_YshExpr -- I guess that's faster
#   - although EvalExpr() can take param.blame_tok


def _DisallowMutableDefault(val, blame_loc):
    # type: (value_t, loc_t) -> None
    if val.tag() in (value_e.List, value_e.Dict):
        raise error.TypeErr(val, "Default values can't be mutable", blame_loc)


def _EvalPosDefaults(expr_ev, pos_params):
    # type: (expr_eval.ExprEvaluator, List[Param]) -> List[value_t]
    """Shared between func and proc: Eval defaults for positional params"""

    no_val = None  # type: value_t
    pos_defaults = [no_val] * len(pos_params)
    for i, p in enumerate(pos_params):
        if p.default_val:
            val = expr_ev.EvalExpr(p.default_val, p.blame_tok)
            _DisallowMutableDefault(val, p.blame_tok)
            pos_defaults[i] = val
    return pos_defaults


def _EvalNamedDefaults(expr_ev, named_params):
    # type: (expr_eval.ExprEvaluator, List[Param]) -> Dict[str, value_t]
    """Shared between func and proc: Eval defaults for named params"""

    named_defaults = NewDict()  # type: Dict[str, value_t]
    for i, p in enumerate(named_params):
        if p.default_val:
            val = expr_ev.EvalExpr(p.default_val, p.blame_tok)
            _DisallowMutableDefault(val, p.blame_tok)
            named_defaults[p.name] = val
    return named_defaults


def EvalFuncDefaults(
        expr_ev,  # type: expr_eval.ExprEvaluator
        func,  # type: Func
):
    # type: (...) -> Tuple[List[value_t], Dict[str, value_t]]
    """Evaluate default args for funcs, at time of DEFINITION, not call."""

    if func.positional:
        pos_defaults = _EvalPosDefaults(expr_ev, func.positional.params)
    else:
        pos_defaults = None

    if func.named:
        named_defaults = _EvalNamedDefaults(expr_ev, func.named.params)
    else:
        named_defaults = None

    return pos_defaults, named_defaults


def EvalProcDefaults(expr_ev, sig):
    # type: (expr_eval.ExprEvaluator, proc_sig.Closed) -> ProcDefaults
    """Evaluate default args for procs, at time of DEFINITION, not call."""

    no_val = None  # type: value_t

    if sig.word:
        word_defaults = [no_val] * len(sig.word.params)
        for i, p in enumerate(sig.word.params):
            if p.default_val:
                val = expr_ev.EvalExpr(p.default_val, p.blame_tok)
                if val.tag() != value_e.Str:
                    raise error.TypeErr(
                        val, 'Default val for word param must be Str',
                        p.blame_tok)

                word_defaults[i] = val
    else:
        word_defaults = None

    if sig.positional:
        pos_defaults = _EvalPosDefaults(expr_ev, sig.positional.params)
    else:
        pos_defaults = None  # in case there's a block param

    if sig.named:
        named_defaults = _EvalNamedDefaults(expr_ev, sig.named.params)
    else:
        named_defaults = None

    # cd /tmp (; ; myblock)
    if sig.block_param:
        exp = sig.block_param.default_val
        if exp:
            block_default = expr_ev.EvalExpr(exp, sig.block_param.blame_tok)
            # It can only be ^() or null
            if block_default.tag() not in (value_e.Null, value_e.Command):
                raise error.TypeErr(
                    block_default,
                    "Default value for block should be Command or Null",
                    sig.block_param.blame_tok)
        else:
            block_default = None  # no default, different than value.Null
    else:
        block_default = None

    return ProcDefaults(word_defaults, pos_defaults, named_defaults,
                        block_default)


def _EvalPosArgs(expr_ev, exprs, pos_args):
    # type: (expr_eval.ExprEvaluator, List[expr_t], List[value_t]) -> None
    """Shared between func and proc: evaluate positional args."""

    for e in exprs:
        UP_e = e
        if e.tag() == expr_e.Spread:
            e = cast(expr.Spread, UP_e)
            val = expr_ev._EvalExpr(e.child)
            if val.tag() != value_e.List:
                raise error.TypeErr(val, 'Spread expected a List', e.left)
            pos_args.extend(cast(value.List, val).items)
        else:
            pos_args.append(expr_ev._EvalExpr(e))


def _EvalNamedArgs(expr_ev, named_exprs):
    # type: (expr_eval.ExprEvaluator, List[NamedArg]) -> Dict[str, value_t]
    """Shared between func and proc: evaluate named args."""

    named_args = NewDict()  # type: Dict[str, value_t]
    for n in named_exprs:
        val_expr = n.value
        UP_val_expr = val_expr
        if val_expr.tag() == expr_e.Spread:
            val_expr = cast(expr.Spread, UP_val_expr)
            val = expr_ev._EvalExpr(val_expr.child)
            if val.tag() != value_e.Dict:
                raise error.TypeErr(val, 'Spread expected a Dict',
                                    val_expr.left)
            named_args.update(cast(value.Dict, val).d)
        else:
            val = expr_ev.EvalExpr(n.value, n.name)
            name = lexer.TokenVal(n.name)
            named_args[name] = val

    return named_args


def _EvalArgList(
        expr_ev,  # type: expr_eval.ExprEvaluator
        args,  # type: ArgList
        me=None  # type: Optional[value_t]
):
    # type: (...) -> Tuple[List[value_t], Optional[Dict[str, value_t]]]
    """Evaluate arg list for funcs.

    This is a PRIVATE METHOD on ExprEvaluator, but it's in THIS FILE, because I
    want it to be next to EvalTypedArgsToProc, which is similar.

    It's not valid to call this without the EvalExpr() wrapper:

      with state.ctx_YshExpr(...)  # required to call this
        ...
    """
    pos_args = []  # type: List[value_t]

    if me:  # self/this argument
        pos_args.append(me)

    _EvalPosArgs(expr_ev, args.pos_args, pos_args)

    named_args = None  # type: Dict[str, value_t]
    if args.named_args is not None:
        named_args = _EvalNamedArgs(expr_ev, args.named_args)

    return pos_args, named_args


def EvalTypedArgsToProc(
        expr_ev,  # type: expr_eval.ExprEvaluator
        mutable_opts,  # type: state.MutableOpts
        node,  # type: command.Simple
        proc_args,  # type: ProcArgs
):
    # type: (...) -> None
    """Evaluate word, typed, named, and block args for a proc."""
    proc_args.typed_args = node.typed_args

    # We only got here if the call looks like
    #    p (x)
    #    p { echo hi }
    #    p () { echo hi }
    # So allocate this unconditionally
    proc_args.pos_args = []

    ty = node.typed_args
    if ty:
        if ty.left.id == Id.Op_LBracket:  # assert [42 === x]
            # Defer evaluation by wrapping in value.Expr

            for exp in ty.pos_args:
                proc_args.pos_args.append(value.Expr(exp))
            # TODO: ...spread is illegal

            n1 = ty.named_args
            if n1 is not None:
                proc_args.named_args = NewDict()
                for named_arg in n1:
                    name = lexer.TokenVal(named_arg.name)
                    proc_args.named_args[name] = value.Expr(named_arg.value)
                # TODO: ...spread is illegal

        else:  # json write (x)
            with state.ctx_YshExpr(mutable_opts):  # What EvalExpr() does
                _EvalPosArgs(expr_ev, ty.pos_args, proc_args.pos_args)

                if ty.named_args is not None:
                    proc_args.named_args = _EvalNamedArgs(
                        expr_ev, ty.named_args)

        if ty.block_expr and node.block:
            e_die("Can't accept both block expression and block literal",
                  node.block.brace_group.left)

        # p ( ; ; block) is an expression to be evaluated
        if ty.block_expr:
            # fallback location is (
            proc_args.block_arg = expr_ev.EvalExpr(ty.block_expr, ty.left)

    # p { echo hi } is an unevaluated block
    if node.block:
        # TODO: conslidate value.Block (holds LiteralBlock) and value.Command
        proc_args.block_arg = value.Block(node.block)

        # Add location info so the cmd_val looks the same for both:
        #   cd /tmp (; ; ^(echo hi))
        #   cd /tmp { echo hi }
        if not proc_args.typed_args:
            proc_args.typed_args = ArgList.CreateNull()

            # Also add locations for error message: ls { echo invalid }
            proc_args.typed_args.left = node.block.brace_group.left
            proc_args.typed_args.right = node.block.brace_group.right


def _BindWords(
        proc_name,  # type: str
        group,  # type: ParamGroup
        defaults,  # type: List[value_t]
        cmd_val,  # type: cmd_value.Argv
        mem,  # type: state.Mem
        blame_loc,  # type: loc_t
):
    # type: (...) -> None

    argv = cmd_val.argv[1:]
    num_args = len(argv)
    for i, p in enumerate(group.params):
        if i < num_args:
            val = value.Str(argv[i])  # type: value_t
        else:  # default args were evaluated on definition
            val = defaults[i]
            if val is None:
                raise error.Expr(
                    "proc %r wasn't passed word param %r" %
                    (proc_name, p.name), blame_loc)

        mem.SetLocalName(LeftName(p.name, p.blame_tok), val)

    # ...rest

    num_params = len(group.params)
    rest = group.rest_of
    if rest:
        lval = LeftName(rest.name, rest.blame_tok)

        items = [value.Str(s)
                 for s in argv[num_params:]]  # type: List[value_t]
        rest_val = value.List(items)
        mem.SetLocalName(lval, rest_val)
    else:
        if num_args > num_params:
            if len(cmd_val.arg_locs):
                # point to the first extra one
                extra_loc = cmd_val.arg_locs[num_params + 1]  # type: loc_t
            else:
                extra_loc = loc.Missing

            # Too many arguments.
            raise error.Expr(
                "proc %r takes %d words, but got %d" %
                (proc_name, num_params, num_args), extra_loc)


def _BindTyped(
        code_name,  # type: str
        group,  # type: Optional[ParamGroup]
        defaults,  # type: List[value_t]
        pos_args,  # type: Optional[List[value_t]]
        mem,  # type: state.Mem
        blame_loc,  # type: loc_t
):
    # type: (...) -> None

    if pos_args is None:
        pos_args = []

    num_args = len(pos_args)
    num_params = 0

    i = 0

    if group:
        for p in group.params:
            if i < num_args:
                val = pos_args[i]
            else:
                val = defaults[i]
                if val is None:
                    raise error.Expr(
                        "%r wasn't passed typed param %r" %
                        (code_name, p.name), blame_loc)

            mem.SetLocalName(LeftName(p.name, p.blame_tok), val)
            i += 1
        num_params += len(group.params)

    # ...rest

    if group:
        rest = group.rest_of
        if rest:
            lval = LeftName(rest.name, rest.blame_tok)

            rest_val = value.List(pos_args[num_params:])
            mem.SetLocalName(lval, rest_val)
        else:
            if num_args > num_params:
                # Too many arguments.
                raise error.Expr(
                    "%r takes %d typed args, but got %d" %
                    (code_name, num_params, num_args), blame_loc)


def _BindNamed(
        code_name,  # type: str
        group,  # type: ParamGroup
        defaults,  # type: Dict[str, value_t]
        named_args,  # type: Optional[Dict[str, value_t]]
        mem,  # type: state.Mem
        blame_loc,  # type: loc_t
):
    # type: (...) -> None

    if named_args is None:
        named_args = NewDict()

    for p in group.params:
        val = named_args.get(p.name)
        if val is None:
            val = defaults.get(p.name)
        if val is None:
            raise error.Expr(
                "%r wasn't passed named param %r" % (code_name, p.name),
                blame_loc)

        mem.SetLocalName(LeftName(p.name, p.blame_tok), val)
        # Remove bound args
        mylib.dict_erase(named_args, p.name)

    # ...rest
    rest = group.rest_of
    if rest:
        lval = LeftName(rest.name, rest.blame_tok)
        mem.SetLocalName(lval, value.Dict(named_args))
    else:
        num_args = len(named_args)
        num_params = len(group.params)
        if num_args > num_params:
            # Too many arguments.
            raise error.Expr(
                "%r takes %d named args, but got %d" %
                (code_name, num_params, num_args), blame_loc)


def _BindFuncArgs(func, rd, mem):
    # type: (value.Func, typed_args.Reader, state.Mem) -> None

    node = func.parsed
    blame_loc = rd.LeftParenToken()

    ### Handle positional args

    if node.positional:
        _BindTyped(func.name, node.positional, func.pos_defaults, rd.pos_args,
                   mem, blame_loc)
    else:
        if rd.pos_args is not None:
            num_pos = len(rd.pos_args)
            if num_pos != 0:
                raise error.Expr(
                    "Func %r takes no positional args, but got %d" %
                    (func.name, num_pos), blame_loc)

    semi = rd.arg_list.semi_tok
    if semi is not None:
        blame_loc = semi

    ### Handle named args

    if node.named:
        _BindNamed(func.name, node.named, func.named_defaults, rd.named_args,
                   mem, blame_loc)
    else:
        if rd.named_args is not None:
            num_named = len(rd.named_args)
            if num_named != 0:
                raise error.Expr(
                    "Func %r takes no named args, but got %d" %
                    (func.name, num_named), blame_loc)


def BindProcArgs(proc, cmd_val, mem):
    # type: (value.Proc, cmd_value.Argv, state.Mem) -> None

    proc_args = cmd_val.proc_args

    UP_sig = proc.sig
    if UP_sig.tag() != proc_sig_e.Closed:  # proc is-closed ()
        return

    sig = cast(proc_sig.Closed, UP_sig)

    # Note: we don't call _BindX() when there is no corresponding param group.
    # This saves a few allocations, because most procs won't have all 3 types
    # of args.

    blame_loc = loc.Missing  # type: loc_t

    ### Handle word args

    if len(cmd_val.arg_locs) > 0:
        blame_loc = cmd_val.arg_locs[0]

    if sig.word:
        _BindWords(proc.name, sig.word, proc.defaults.for_word, cmd_val, mem,
                   blame_loc)
    else:
        num_word = len(cmd_val.argv)
        if num_word != 1:
            raise error.Expr(
                "Proc %r takes no word args, but got %d" %
                (proc.name, num_word - 1), blame_loc)

    ### Handle typed positional args.  This includes a block arg, if any.

    if proc_args and proc_args.typed_args:  # blame ( of call site
        blame_loc = proc_args.typed_args.left

    pos_args = proc_args.pos_args if proc_args else None
    if sig.positional:  # or sig.block_param:
        _BindTyped(proc.name, sig.positional, proc.defaults.for_typed,
                   pos_args, mem, blame_loc)
    else:
        if pos_args is not None:
            num_pos = len(pos_args)
            if num_pos != 0:
                raise error.Expr(
                    "Proc %r takes no typed args, but got %d" %
                    (proc.name, num_pos), blame_loc)

    ### Handle typed named args

    if proc_args and proc_args.typed_args:  # blame ; of call site if possible
        semi = proc_args.typed_args.semi_tok
        if semi is not None:
            blame_loc = semi

    named_args = proc_args.named_args if proc_args else None
    if sig.named:
        _BindNamed(proc.name, sig.named, proc.defaults.for_named, named_args,
                   mem, blame_loc)
    else:
        if named_args is not None:
            num_named = len(named_args)
            if num_named != 0:
                raise error.Expr(
                    "Proc %r takes no named args, but got %d" %
                    (proc.name, num_named), blame_loc)

    # Maybe blame second ; of call site.  Because value_t doesn't generally
    # have location info, as opposed to expr_t.
    if proc_args and proc_args.typed_args:
        semi = proc_args.typed_args.semi_tok2
        if semi is not None:
            blame_loc = semi

    ### Handle block arg

    block_param = sig.block_param
    block_arg = proc_args.block_arg if proc_args else None

    if block_param:
        if block_arg is None:
            block_arg = proc.defaults.for_block
        if block_arg is None:
            raise error.Expr(
                "%r wasn't passed block param %r" %
                (proc.name, block_param.name), blame_loc)

        mem.SetLocalName(LeftName(block_param.name, block_param.blame_tok),
                         block_arg)

    else:
        if block_arg is not None:
            raise error.Expr(
                "Proc %r doesn't accept a block argument" % proc.name,
                blame_loc)


def CallUserFunc(
        func,  # type: value.Func
        rd,  # type: typed_args.Reader
        mem,  # type: state.Mem
        cmd_ev,  # type: cmd_eval.CommandEvaluator
):
    # type: (...) -> value_t

    # Push a new stack frame

    # TODO: ctx_Eval() can replace io with DummyIO type!  It can possibly
    # implement __getattr__ and __get_mutating__?
    with state.ctx_FuncCall(mem, func):
        _BindFuncArgs(func, rd, mem)

        try:
            cmd_ev._Execute(func.parsed.body)

            return value.Null  # implicit return
        except vm.ValueControlFlow as e:
            return e.value
        except vm.IntControlFlow as e:
            raise AssertionError('IntControlFlow in func')

    raise AssertionError('unreachable')


# vim: sw=4
