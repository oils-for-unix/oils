#!/usr/bin/env python2
"""
code.py: User-defined funcs and procs
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import (value, value_t, scope_e, lvalue,
                                        cmd_value, FuncValue, ProcDefaults)
from _devbuild.gen.syntax_asdl import (proc_sig, proc_sig_e, Func, loc,
                                       ArgList, expr, expr_e)

from core import error
from core.error import e_die, e_die_status
from core import state
from core import vm
from frontend import lexer
from frontend import typed_args
from mycpp.mylib import log

from typing import List, Tuple, Dict, Optional, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import command, loc_t
    from _devbuild.gen.runtime_asdl import ProcValue
    from core import ui
    from osh import cmd_eval
    from ysh import expr_eval

_ = log


def EvalProcDefaults(expr_ev, sig):
    # type: (expr_eval.ExprEvaluator, proc_sig.Closed) -> ProcDefaults
    """Evaluated at time of proc DEFINITION, not time of call."""

    no_val = None  # type: value_t

    # TODO: ensure these are STRINGS
    word_defaults = [no_val] * len(sig.word_params)
    for i, p in enumerate(sig.word_params):
        if p.default_val:
            val = expr_ev.EvalExpr(p.default_val, loc.Missing)
            word_defaults[i] = val

    # TODO: remove the mutable default issue that Python has: f(x=[])
    # Whitelist Bool, Int, Float, Str.
    pos_defaults = [no_val] * len(sig.pos_params)
    for i, p in enumerate(sig.pos_params):
        if p.default_val:
            val = expr_ev.EvalExpr(p.default_val, loc.Missing)
            pos_defaults[i] = val

    # Block param is treated like another positional param, so you can also
    # pass it
    #    cd /tmp (myblock)
    if sig.block_param:
        exp = sig.block_param.default_val
        if exp:
            val = expr_ev.EvalExpr(exp, loc.Missing)
        else:
            val = None  # no default, different than value.Null
        pos_defaults.append(val)

    named_defaults = {}  # Dict[str, value_t]
    for i, p in enumerate(sig.named_params):
        if p.default_val:
            val = expr_ev.EvalExpr(p.default_val, loc.Missing)
            named_defaults[p.name] = val

    return ProcDefaults(word_defaults, pos_defaults, named_defaults)


def EvalFuncDefaults(
        expr_ev,  # type: expr_eval.ExprEvaluator
        func,  # type: Func
):
    # type: (...) -> Tuple[List[value_t], Dict[str, value_t]]

    no_val = None  # type: value_t

    # TODO: remove the mutable default issue that Python has: f(x=[]) Whitelist
    # Bool, Int, Float, Str.

    pos_defaults = [no_val] * len(func.pos_params)
    for i, p in enumerate(func.pos_params):
        if p.default_val:
            val = expr_ev.EvalExpr(p.default_val, loc.Missing)
            pos_defaults[i] = val

    named_defaults = {}  # Dict[str, value_t]
    for i, p in enumerate(func.named_params):
        if p.default_val:
            val = expr_ev.EvalExpr(p.default_val, loc.Missing)
            named_defaults[p.name] = val

    return pos_defaults, named_defaults


def _EvalArgList(
        expr_ev,  # type: expr_eval.ExprEvaluator
        args,  # type: ArgList
        me=None  # type: Optional[value_t]
):
    # type: (...) -> Tuple[List[value_t], Dict[str, value_t]]
    """ 
    This is a PRIVATE METHOD on ExprEvaluator, but it's in THIS FILE, because I
    want it to be next to EvalTypedArgsToProc, which is similar.

    It's not valid to call this without the PUBLIC EvalExpr() wrapper:

      with state.ctx_YshExpr(...)  # required to call this
    """
    pos_args = []  # type: List[value_t]

    if me:  # self/this argument
        pos_args.append(me)

    for arg in args.pos_args:
        UP_arg = arg

        if arg.tag() == expr_e.Spread:
            arg = cast(expr.Spread, UP_arg)
            # assume it returns a list
            #pos_args.extend(self._EvalExpr(arg.child))
            pass
        else:
            pos_args.append(expr_ev._EvalExpr(arg))

    kwargs = {}  # type: Dict[str, value_t]

    # NOTE: Keyword args aren't tested
    if 0:
        for named in args.named:
            if named.name:
                kwargs[named.name.tval] = expr_ev._EvalExpr(named.value)
            else:
                # ...named
                kwargs.update(expr_ev._EvalExpr(named.value))

    return pos_args, kwargs


def EvalTypedArgsToProc(expr_ev, node, cmd_val):
    # type: (expr_eval.ExprEvaluator, command.Simple, cmd_value.Argv) -> None
    """
    TODO: Synchronize with _EvalArgList() in ysh/expr_eval.py
    """
    cmd_val.typed_args = node.typed_args

    ty = node.typed_args
    if ty:
        if ty.left.id == Id.Op_LBracket:  # assert [42 === x]
            # Defer evaluation by wrapping in value.Expr

            # TODO: save allocs
            cmd_val.pos_args = []
            for exp in ty.pos_args:
                cmd_val.pos_args.append(value.Expr(exp))

            # TODO: save allocs
            cmd_val.named_args = {}
            for named_arg in node.typed_args.named_args:
                name = lexer.TokenVal(named_arg.name)
                cmd_val.named_args[name] = value.Expr(named_arg.value)

        else:  # json write (x)
            # TODO: save on allocations if no pos args
            cmd_val.pos_args = []
            for i, pos_arg in enumerate(ty.pos_args):
                val = expr_ev.EvalExpr(pos_arg, loc.Missing)
                cmd_val.pos_args.append(val)

            # TODO: save on allocations if no named args
            cmd_val.named_args = {}
            for named_arg in ty.named_args:
                val = expr_ev.EvalExpr(named_arg.value, named_arg.name)
                name = lexer.TokenVal(named_arg.name)
                cmd_val.named_args[name] = val

    # Pass the unevaluated block.
    if node.block:
        if cmd_val.pos_args is None:  # TODO: remove
            cmd_val.pos_args = []
        cmd_val.pos_args.append(value.Block(node.block))

        # Important invariant: cmd_val look the same for
        #   eval (^(echo hi))
        #   eval { echo hi }
        if not cmd_val.typed_args:
            cmd_val.typed_args = ArgList.CreateNull()

            # Also add locations for error message: ls { echo invalid }
            cmd_val.typed_args.left = node.block.brace_group.left
            cmd_val.typed_args.right = node.block.brace_group.right


def _BindFuncArgs(func_name, node, rd, mem):
    # type: (str, Func, typed_args.Reader, state.Mem) -> None

    # TODO:
    # - Handle default args.  Evaluate them here or elsewhere?
    # - pass named args

    num_pos_params = len(node.pos_params)

    pos_args = rd.pos_args
    num_args = len(pos_args)

    blame_loc = rd.LeftParenToken()
    if node.rest_of_pos:
        if num_args < num_pos_params:
            raise error.TypeErrVerbose(
                "%s() expects at least %d arguments, but got %d" %
                (func_name, num_pos_params, num_args), blame_loc)
    elif num_args != num_pos_params:
        raise error.TypeErrVerbose(
            "%s() expects %d arguments, but got %d" %
            (func_name, num_pos_params, num_args), blame_loc)

    num_args = len(node.pos_params)
    for i in xrange(0, num_args):
        pos_param = node.pos_params[i]
        lval = lvalue.Named(pos_param.name, pos_param.blame_tok)

        pos_arg = pos_args[i]
        mem.SetValue(lval, pos_arg, scope_e.LocalOnly)

    if node.rest_of_pos:
        p = node.rest_of_pos
        lval = lvalue.Named(p.name, p.blame_tok)

        rest_val = value.List(pos_args[num_args:])
        mem.SetValue(lval, rest_val, scope_e.LocalOnly)

    num_params = len(node.named_params)
    named_args = rd.named_args
    num_args = len(named_args)

    if num_args != num_params:
        raise error.TypeErrVerbose(
            "%s() expects %d named arguments, but got %d" %
            (func_name, num_params, num_args), blame_loc)



def BindProcArgs(proc, cmd_val, mem, errfmt):
    # type: (ProcValue, cmd_value.Argv, state.Mem, ui.ErrorFormatter) -> None

    UP_sig = proc.sig
    if UP_sig.tag() != proc_sig_e.Closed:  # proc is-closed ()
        return

    sig = cast(proc_sig.Closed, UP_sig)

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

            val = proc.defaults.for_word[i]
            if val is None:
                e_die("No value provided for param %r" % p.name, p.blame_tok)

        if is_out_param:
            flags = state.SetNameref
        else:
            flags = 0

        #log('flags %s', flags)
        mem.SetValue(lvalue.Named(param_name, p.blame_tok),
                     val,
                     scope_e.LocalOnly,
                     flags=flags)

    num_params = len(sig.word_params)
    if sig.rest_of_words:
        r = sig.rest_of_words
        lval = lvalue.Named(r.name, r.blame_tok)

        items = [value.Str(s)
                 for s in argv[num_params:]]  # type: List[value_t]
        rest_val = value.List(items)
        mem.SetValue(lval, rest_val, scope_e.LocalOnly)
    else:
        if num_args > num_params:
            if len(cmd_val.arg_locs):
                arg0_loc = cmd_val.arg_locs[num_args]  # type: loc_t
            else:
                arg0_loc = loc.Missing

            # Too many arguments.
            e_die_status(2,
                "proc %r expected %d arguments, but got %d" %
                (proc.name, num_params, num_args), arg0_loc)


def CallUserFunc(func, rd, mem, cmd_ev):
    # type: (FuncValue, typed_args.Reader, state.Mem, cmd_eval.CommandEvaluator) -> value_t

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
