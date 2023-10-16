#!/usr/bin/env python2
"""
code.py: User-defined funcs and procs
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import (value, value_e, value_t, scope_e,
                                        lvalue, cmd_value, ProcDefaults)
from _devbuild.gen.syntax_asdl import (proc_sig, proc_sig_e, Param, NamedArg,
                                       Func, loc, ArgList, expr, expr_e,
                                       expr_t)

from core import error
from core.error import e_die, e_die_status
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
# - Bind func params
# - validate defaults
#   - remove mutable defaults that Python has: f(x=[]) Whitelist Bool,
#     Int, Float, Str, and I suppose cmd, eggex, etc.
#   - validate Block arg default
# - e_die{,_status} -> error.Expr uniformly
# - fix locations -- test-proc-missing, test-func-missing
# - use _EvalExpr consistently, I think
#   - a single with state.ctx_YshExpr -- I guess that's faster

def _EvalPosDefaults(expr_ev, pos_params):
    # type: (expr_eval.ExprEvaluator, List[Param]) -> List[value_t]
    """Shared between func and proc: Eval defaults for positional params"""

    no_val = None  # type: value_t
    pos_defaults = [no_val] * len(pos_params)
    for i, p in enumerate(pos_params):
        if p.default_val:
            val = expr_ev.EvalExpr(p.default_val, loc.Missing)
            pos_defaults[i] = val
    return pos_defaults


def _EvalNamedDefaults(expr_ev, named_params):
    # type: (expr_eval.ExprEvaluator, List[Param]) -> Dict[str, value_t]
    """Shared between func and proc: Eval defaults for named params"""

    named_defaults = NewDict()  # type: Dict[str, value_t]
    for i, p in enumerate(named_params):
        if p.default_val:
            val = expr_ev.EvalExpr(p.default_val, loc.Missing)
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

    word_defaults = [no_val] * len(sig.word_params)
    for i, p in enumerate(sig.word_params):
        if p.default_val:
            val = expr_ev.EvalExpr(p.default_val, loc.Missing)
            if val.tag() != value_e.Str:
                raise error.TypeErr(val,
                                    'Default val for word param must be Str',
                                    p.blame_tok)

            word_defaults[i] = val

    pos_defaults = _EvalPosDefaults(expr_ev, sig.pos_params)

    # Block param is treated like another positional param, so you can also
    # pass it
    #    cd /tmp (myblock)
    if sig.block_param:
        exp = sig.block_param.default_val
        if exp:
            val = expr_ev.EvalExpr(exp, loc.Missing)
            # TODO: it can only be ^() or null
        else:
            val = None  # no default, different than value.Null
        pos_defaults.append(val)

    named_defaults = _EvalNamedDefaults(expr_ev, sig.named_params)

    return ProcDefaults(word_defaults, pos_defaults, named_defaults)


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
                raise error.TypeErr(val, 'Spread expected a dict',
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
        cmd_val,  # type: cmd_value.Argv
):
    # type: (...) -> None
    """Evaluate word, typed, named, and block args for a proc."""
    cmd_val.typed_args = node.typed_args

    # We only got here if the call looks like
    #    p (x)
    #    p { echo hi }
    #    p () { echo hi }
    # So allocate this unconditionally
    cmd_val.pos_args = []

    ty = node.typed_args
    if ty:
        if ty.left.id == Id.Op_LBracket:  # assert [42 === x]
            # Defer evaluation by wrapping in value.Expr

            for exp in ty.pos_args:
                cmd_val.pos_args.append(value.Expr(exp))
            # TODO: ...spread is illegal

            n1 = ty.named_args
            if n1 is not None:
                cmd_val.named_args = NewDict()
                for named_arg in n1:
                    name = lexer.TokenVal(named_arg.name)
                    cmd_val.named_args[name] = value.Expr(named_arg.value)
                # TODO: ...spread is illegal

        else:  # json write (x)
            with state.ctx_YshExpr(mutable_opts):  # What EvalExpr() does
                _EvalPosArgs(expr_ev, ty.pos_args, cmd_val.pos_args)

                n2 = ty.named_args
                if ty.named_args is not None:
                    cmd_val.named_args = _EvalNamedArgs(expr_ev, ty.named_args)

    # Pass the unevaluated block.
    if node.block:
        cmd_val.pos_args.append(value.Block(node.block))

        # Important invariant: cmd_val look the same for
        #   eval (^(echo hi))
        #   eval { echo hi }
        if not cmd_val.typed_args:
            cmd_val.typed_args = ArgList.CreateNull()

            # Also add locations for error message: ls { echo invalid }
            cmd_val.typed_args.left = node.block.brace_group.left
            cmd_val.typed_args.right = node.block.brace_group.right


def _BindWords(
        proc_name,  # type: str
        sig,  # type: proc_sig.Closed
        defaults,  # type: List[value_t]
        cmd_val,  # type: cmd_value.Argv
        mem,  # type: state.Mem
):
    # type: (...) -> None

    argv = cmd_val.argv[1:]
    num_args = len(argv)
    for i, p in enumerate(sig.word_params):

        # proc p(out Ref)
        is_out_param = (p.type is not None and p.type.name == 'Ref')
        #log('is_out %s', is_out_param)

        param_name = p.name  # may get hidden __
        if i < num_args:
            arg_str = argv[i]

            # If we have myproc(p), and call it with myproc :arg, then bind
            # __p to 'arg'.  That is, the param has a prefix ADDED, and the arg
            # has a prefix REMOVED.
            #
            # This helps eliminate "nameref cycles".
            if is_out_param:
                param_name = '__' + param_name

                if not arg_str.startswith(':'):
                    # TODO: Point to the exact argument.  We got argv but not
                    # locations.
                    e_die(
                        'Ref param %r expected arg starting with colon : but got %r'
                        % (p.name, arg_str))

                arg_str = arg_str[1:]

            val = value.Str(arg_str)  # type: value_t
            #log('%s -> %s', param_name, val)
        else:
            # default args were evaluated on definition

            val = defaults[i]
            if val is None:
                e_die(
                    "proc %r wasn't passed word param %r" %
                    (proc_name, p.name), loc.Missing)

        if is_out_param:
            flags = state.SetNameref
        else:
            flags = 0

        #log('flags %s', flags)
        mem.SetValue(lvalue.Named(param_name, p.blame_tok),
                     val,
                     scope_e.LocalOnly,
                     flags=flags)

    # ...rest

    num_params = len(sig.word_params)
    rest = sig.rest_of_words
    if rest:
        lval = lvalue.Named(rest.name, rest.blame_tok)

        items = [value.Str(s)
                 for s in argv[num_params:]]  # type: List[value_t]
        rest_val = value.List(items)
        mem.SetValue(lval, rest_val, scope_e.LocalOnly)
    else:
        if num_args > num_params:
            if len(cmd_val.arg_locs):
                # point to the first extra one
                extra_loc = cmd_val.arg_locs[num_params + 1]  # type: loc_t
            else:
                extra_loc = loc.Missing

            # Too many arguments.
            e_die_status(
                2, "proc %r expected %d words, but got %d" %
                (proc_name, num_params, num_args), extra_loc)


def _BindTyped(
        code_name,  # type: str
        sig,  # type: proc_sig.Closed
        defaults,  # type: List[value_t]
        pos_args,  # type: Optional[List[value_t]]
        mem,  # type: state.Mem
):
    # type: (...) -> None

    if pos_args is None:
        pos_args = []

    num_args = len(pos_args)

    i = 0
    for p in sig.pos_params:
        if i < num_args:
            val = pos_args[i]
        else:
            val = defaults[i]
            if val is None:
                # TODO: better location
                e_die("%r wasn't passed typed param %r" % (code_name, p.name),
                      loc.Missing)

        mem.SetValue(lvalue.Named(p.name, p.blame_tok), val, scope_e.LocalOnly)
        i += 1

    # Special case: treat block param like the next positional arg
    if sig.block_param:
        p = sig.block_param

        if i < num_args:
            val = pos_args[i]
        else:
            val = defaults[i]
            if val is None:
                # TODO: better location
                e_die("%r wasn't passed block param %r" % (code_name, p.name),
                      loc.Missing)

        mem.SetValue(lvalue.Named(p.name, p.blame_tok), val, scope_e.LocalOnly)

    num_params = len(sig.pos_params)
    if sig.block_param:
        num_params += 1

    # ...rest

    rest = sig.rest_of_pos
    if rest:
        lval = lvalue.Named(rest.name, rest.blame_tok)

        rest_val = value.List(pos_args[num_params:])
        mem.SetValue(lval, rest_val, scope_e.LocalOnly)
    else:
        if num_args > num_params:
            # Too many arguments.
            # TODO: better location
            e_die_status(
                2, "%r expected %d typed args, but got %d" %
                (code_name, num_params, num_args), loc.Missing)


def _BindNamed(
        code_name,  # type: str
        sig,  # type: proc_sig.Closed
        defaults,  # type: Dict[str, value_t]
        named_args,  # type: Optional[Dict[str, value_t]]
        mem,  # type: state.Mem
):
    # type: (...) -> None

    if named_args is None:
        named_args = NewDict()

    for p in sig.named_params:
        val = named_args.get(p.name)
        if val is None:
            val = defaults.get(p.name)
        if val is None:
            # TODO: better location
            e_die("%r wasn't passed named param %r" % (code_name, p.name),
                  loc.Missing)

        mem.SetValue(lvalue.Named(p.name, p.blame_tok), val, scope_e.LocalOnly)
        # Remove bound args
        mylib.dict_erase(named_args, p.name)

    # ...rest
    rest = sig.rest_of_named
    if rest:
        lval = lvalue.Named(rest.name, rest.blame_tok)
        mem.SetValue(lval, value.Dict(named_args), scope_e.LocalOnly)


def _BindFuncArgs(func_name, node, rd, mem):
    # type: (str, Func, typed_args.Reader, state.Mem) -> None

    #_BindTyped(func_name, sig, proc.defaults.for_typed, cmd_val.pos_args, mem)

    #_BindNamed(proc.name, sig, proc.defaults.for_named, cmd_val.named_args, mem)

    # TODO:
    # - Handle default args.  Evaluate them here or elsewhere?
    # - pass named args

    posit = node.positional
    if not posit:
        return

    num_pos_params = len(posit.params)

    pos_args = rd.pos_args
    num_args = len(pos_args)

    blame_loc = rd.LeftParenToken()
    if posit.rest_of:
        if num_args < num_pos_params:
            raise error.TypeErrVerbose(
                "%s() expects at least %d arguments, but got %d" %
                (func_name, num_pos_params, num_args), blame_loc)
    elif num_args != num_pos_params:
        raise error.TypeErrVerbose(
            "%s() expects %d arguments, but got %d" %
            (func_name, num_pos_params, num_args), blame_loc)

    num_args = len(posit.params)
    for i in xrange(0, num_args):
        pos_param = posit.params[i]
        lval = lvalue.Named(pos_param.name, pos_param.blame_tok)

        pos_arg = pos_args[i]
        mem.SetValue(lval, pos_arg, scope_e.LocalOnly)

    if posit.rest_of:
        r = posit.rest_of
        lval = lvalue.Named(r.name, r.blame_tok)

        rest_val = value.List(pos_args[num_args:])
        mem.SetValue(lval, rest_val, scope_e.LocalOnly)

    if node.named:
        num_params = len(node.named.params)
        named_args = rd.named_args
        num_args = len(named_args)

        if num_args != num_params:
            raise error.TypeErrVerbose(
                "%s() expects %d named arguments, but got %d" %
                (func_name, num_params, num_args), blame_loc)


def BindProcArgs(proc, cmd_val, mem):
    # type: (value.Proc, cmd_value.Argv, state.Mem) -> None

    UP_sig = proc.sig
    if UP_sig.tag() != proc_sig_e.Closed:  # proc is-closed ()
        return

    sig = cast(proc_sig.Closed, UP_sig)

    _BindWords(proc.name, sig, proc.defaults.for_word, cmd_val, mem)

    # This includes the block arg
    _BindTyped(proc.name, sig, proc.defaults.for_typed, cmd_val.pos_args, mem)

    _BindNamed(proc.name, sig, proc.defaults.for_named, cmd_val.named_args,
               mem)


def CallUserFunc(func, rd, mem, cmd_ev):
    # type: (value.Func, typed_args.Reader, state.Mem, cmd_eval.CommandEvaluator) -> value_t

    # Push a new stack frame
    with state.ctx_FuncCall(mem, func):
        _BindFuncArgs(func.name, func.parsed, rd, mem)

        try:
            cmd_ev._Execute(func.parsed.body)

            return value.Null  # implicit return
        except vm.ValueControlFlow as e:
            return e.value
        except vm.IntControlFlow as e:
            raise AssertionError('IntControlFlow in func')

    raise AssertionError('unreachable')
