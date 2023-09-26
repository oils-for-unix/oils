#!/usr/bin/env python2
"""
code.py: User-defined funcs and procs
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, value_t, scope_e, lvalue
from _devbuild.gen.syntax_asdl import ArgList, proc_sig, proc_sig_e

from core import error
from core.error import e_die
from core import state
from core import vm
from frontend import typed_args
from mycpp.mylib import log
from ysh import expr_eval

from typing import List, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import command, loc_t
    from _devbuild.gen.runtime_asdl import Proc
    from core import ui
    from osh import cmd_eval

_ = log


class UserFunc(vm._Callable):
    """A user-defined function."""

    def __init__(self, name, node, mem, cmd_ev):
        # type: (str, command.Func, state.Mem, cmd_eval.CommandEvaluator) -> None
        self.name = name
        self.node = node
        self.cmd_ev = cmd_ev
        self.mem = mem

    def Call(self, args):
        # type: (typed_args.Reader) -> value_t
        pos_args = args.RestPos()
        num_args = len(pos_args)
        num_params = len(self.node.pos_params)

        # TODO: this is the location of 'func', not the CALL.  Should add that
        # location to typed_args.Reader

        blame_loc = self.node.keyword

        if self.node.rest_of_pos:
            if num_args < num_params:
                raise error.TypeErrVerbose(
                    "%s() expects at least %d arguments but %d were given" %
                    (self.name, num_params, num_args), blame_loc)
        elif num_args != num_params:
            raise error.TypeErrVerbose(
                "%s() expects %d arguments but %d were given" %
                (self.name, num_params, num_args), blame_loc)

        named_args = args.RestNamed()
        args.Done()
        num_args = len(named_args)
        num_params = len(self.node.named_params)
        if num_args != num_params:
            raise error.TypeErrVerbose(
                "%s() expects %d named arguments but %d were given" %
                (self.name, num_params, num_args), blame_loc)

        # Push a new stack frame
        with state.ctx_FuncCall(self.cmd_ev.mem, self):

            # TODO: Handle default args.  Evaluate them here or elsewhere?

            num_args = len(self.node.pos_params)
            for i in xrange(0, num_args):
                pos_param = self.node.pos_params[i]
                lval = lvalue.Named(pos_param.name, pos_param.blame_tok)

                pos_arg = pos_args[i]
                self.mem.SetValue(lval, pos_arg, scope_e.LocalOnly)

            if self.node.rest_of_pos:
                p = self.node.rest_of_pos
                lval = lvalue.Named(p.name, p.blame_tok)

                rest_val = value.List(pos_args[num_args:])
                self.mem.SetValue(lval, rest_val, scope_e.LocalOnly)

            # TODO: pass named args

            try:
                self.cmd_ev._Execute(self.node.body)

                return value.Null  # implicit return
            except vm.ValueControlFlow as e:
                return e.value
            except vm.IntControlFlow as e:
                raise AssertionError('IntControlFlow in func')

        raise AssertionError('unreachable')


def BindProcArgs(proc, argv, arg0_loc, args, mem, errfmt, expr_ev):
    # type: (Proc, List[str], loc_t, ArgList, state.Mem, ui.ErrorFormatter, expr_eval.ExprEvaluator) -> int

    UP_sig = proc.sig
    if UP_sig.tag() != proc_sig_e.Closed:  # proc is-closed ()
        return 0

    sig = cast(proc_sig.Closed, UP_sig)

    #print(sig)

    t = typed_args.ReaderFromArgv(argv, args, expr_ev)

    nwords = t.NumWords()
    for i, p in enumerate(sig.word_params):
        # proc p(out Ref)
        is_out_param = (p.type is not None and p.type.name == 'Ref')
        #log('is_out %s', is_out_param)

        param_name = p.name  # may get hidden __

        val = None  # type: value_t

        if i >= nwords:
            if not p.default_val:
                break  # Will raise when we call t.Done()

            # Not sure how this will behave... disallowing it for now
            assert not is_out_param, "Out params cannot have default values"

            val = proc.defaults[i]

        else:
            arg_str = t.Word()

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
                    e_die('Ref param %r expected arg starting with colon : but got %r' %
                          (p.name, arg_str))

                arg_str = arg_str[1:]

            val = value.Str(arg_str)

        if is_out_param:
            flags = state.SetNameref
        else:
            flags = 0

        mem.SetValue(lvalue.Named(param_name, p.blame_tok),
                     val,
                     scope_e.LocalOnly,
                     flags=flags)

    if sig.rest_of_words:
        rest_words = t.RestWords()
        val = value.List([value.Str(x) for x in rest_words])

        mem.SetValue(lvalue.Named(sig.rest_of_words.name, sig.rest_of_words.blame_tok),
                     val,
                     scope_e.LocalOnly)

    npos = t.NumPos()
    for i, p in enumerate(sig.pos_params):
        if i >= npos and p.default_val:
            v = expr_ev.EvalExpr(p.default_val, p.blame_tok)
        else:
            v = t.PosValue()

        mem.SetValue(lvalue.Named(p.name, p.blame_tok),
                     v,
                     scope_e.LocalOnly)

    if sig.rest_of_pos:
        rest_pos = t.RestPos()
        v = value.List(rest_pos)

        mem.SetValue(lvalue.Named(sig.rest_of_pos.name, sig.rest_of_pos.blame_tok),
                     v,
                     scope_e.LocalOnly)

    for n in sig.named_params:
        default_ = None  # type: value_t
        if n.default_val:
            default_ = expr_ev.EvalExpr(n.default_val, n.blame_tok)

        v = t.NamedValue(n.name, default_)

        mem.SetValue(lvalue.Named(n.name, n.blame_tok),
                     v,
                     scope_e.LocalOnly)

    if sig.rest_of_named:
        rest_named = t.RestNamed()
        v = value.Dict(rest_named)

        mem.SetValue(lvalue.Named(sig.rest_of_named.name, sig.rest_of_named.blame_tok),
                     v,
                     scope_e.LocalOnly)

    if sig.block_param:
        b = t.Block()

        mem.SetValue(lvalue.Named(sig.block_param.name, sig.block_param.blame_tok),
                     value.Block(b),
                     scope_e.LocalOnly)

    try:
        t.Done()
    except error.Usage as err:
        err.location = arg0_loc  # TEMP: We should be passing locs to Reader
        errfmt.PrettyPrintError(err)
        return 2

    """
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
                    e_die('Ref param %r expected arg starting with colon : but got %r' %
                          (p.name, arg_str))

                arg_str = arg_str[1:]

            val = value.Str(arg_str)  # type: value_t
            #log('%s -> %s', param_name, val)
        else:
            # default args were evaluated on definition

            val = proc.defaults[i]
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

        items = [value.Str(s) for s in argv[num_params:]]  # type: List[value_t]
        rest_val = value.List(items)
        mem.SetValue(lval, rest_val, scope_e.LocalOnly)
    else:
        if num_args > num_params:
            # TODO: Raise an exception?
            errfmt.Print_(
                "proc %r expected %d arguments, but got %d" %
                (proc.name, num_params, num_args), arg0_loc)
            # This should be status 2 because it's like a usage error.
            return 2
    """

    return 0
