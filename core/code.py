#!/usr/bin/env python2
"""
code.py: User-defined funcs and procs
"""
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.runtime_asdl import (value, value_e, value_t, scope_e,
                                        lvalue, cmd_value, FuncValue,
                                        ProcDefaults)
from _devbuild.gen.syntax_asdl import (proc_sig, proc_sig_e, Func, loc,
                                       ArgList, expr, expr_e)

from core import error
from core.error import e_die, e_die_status
from core import state
from core import vm
from frontend import lexer
from frontend import typed_args
from mycpp.mylib import log, NewDict

from typing import List, Tuple, Dict, Optional, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import command, loc_t
    from _devbuild.gen.runtime_asdl import ProcValue
    from osh import cmd_eval
    from ysh import expr_eval

_ = log


def EvalFuncDefaults(
        expr_ev,  # type: expr_eval.ExprEvaluator
        func,  # type: Func
):
    # type: (...) -> Tuple[List[value_t], Dict[str, value_t]]
    """Evaluate default args for funcs, at time of DEFINITION, not call."""

    no_val = None  # type: value_t

    # TODO: remove the mutable default issue that Python has: f(x=[]) Whitelist
    # Bool, Int, Float, Str.

    pos_defaults = [no_val] * len(func.pos_params)
    for i, p in enumerate(func.pos_params):
        if p.default_val:
            val = expr_ev.EvalExpr(p.default_val, loc.Missing)
            pos_defaults[i] = val

    named_defaults = NewDict()  # type: Dict[str, value_t]
    for i, p in enumerate(func.named_params):
        if p.default_val:
            val = expr_ev.EvalExpr(p.default_val, loc.Missing)
            named_defaults[p.name] = val

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
                raise error.TypeErr(
                        val, 'Default val for word param must be Str',
                        p.blame_tok)

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
            # TODO: it can only be ^() or null
        else:
            val = None  # no default, different than value.Null
        pos_defaults.append(val)

    #log('pos_defaults %s', pos_defaults)

    named_defaults = NewDict()  # type: Dict[str, value_t]
    for i, p in enumerate(sig.named_params):
        if p.default_val:
            val = expr_ev.EvalExpr(p.default_val, loc.Missing)
            named_defaults[p.name] = val

    return ProcDefaults(word_defaults, pos_defaults, named_defaults)


def _EvalArgList(
        expr_ev,  # type: expr_eval.ExprEvaluator
        args,  # type: ArgList
        me=None  # type: Optional[value_t]
):
    # type: (...) -> Tuple[List[value_t], Dict[str, value_t]]
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

    for arg in args.pos_args:
        UP_arg = arg

        if arg.tag() == expr_e.Spread:
            arg = cast(expr.Spread, UP_arg)
            # assume it returns a list
            #pos_args.extend(self._EvalExpr(arg.child))
            pass
        else:
            pos_args.append(expr_ev._EvalExpr(arg))

    kwargs = NewDict()  # type: Dict[str, value_t]

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
            for i, pos_arg in enumerate(ty.pos_args):
                val = expr_ev.EvalExpr(pos_arg, loc.Missing)
                cmd_val.pos_args.append(val)
            # TODO: ...spread

            n2 = ty.named_args
            if n2 is not None:
                cmd_val.named_args = NewDict()
                for named_arg in n2:
                    val = expr_ev.EvalExpr(named_arg.value, named_arg.name)
                    name = lexer.TokenVal(named_arg.name)
                    cmd_val.named_args[name] = val
                # TODO: ...spread

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
                e_die("No value provided for word param %r" % p.name, p.blame_tok)

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
            e_die_status(2,
                "proc %r expected %d words, but got %d" %
                (proc_name, num_params, num_args), extra_loc)


def _BindTyped(
        proc_name,  # type: str
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
                e_die("No value provided for typed param %r" % p.name, loc.Missing)

        mem.SetValue(lvalue.Named(p.name, p.blame_tok),
                     val,
                     scope_e.LocalOnly)
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
                e_die("No value provided for block param %r" % p.name, loc.Missing)

        mem.SetValue(lvalue.Named(p.name, p.blame_tok),
                     val,
                     scope_e.LocalOnly)

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
            e_die_status(2,
                "proc %r expected %d typed args, but got %d" %
                (proc_name, num_params, num_args), loc.Missing)


def _BindNamed(
        proc_name,  # type: str
        sig,  # type: proc_sig.Closed
        defaults,  # type: Dict[str, value_t]
        named_args,  # type: Optional[Dict[str, value_t]]
        mem,  # type: state.Mem
):
    # type: (...) -> None

    if named_args is None:
        named_args = NewDict()

    # TODO: bind


def BindProcArgs(proc, cmd_val, mem):
    # type: (ProcValue, cmd_value.Argv, state.Mem) -> None

    UP_sig = proc.sig
    if UP_sig.tag() != proc_sig_e.Closed:  # proc is-closed ()
        return

    sig = cast(proc_sig.Closed, UP_sig)

    _BindWords(proc.name, sig, proc.defaults.for_word, cmd_val, mem)

    # This includes the block arg
    _BindTyped(proc.name, sig, proc.defaults.for_typed, cmd_val.pos_args, mem)

    _BindNamed(proc.name, sig, proc.defaults.for_named, cmd_val.named_args, mem)


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
