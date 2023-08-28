#!/usr/bin/env python2
"""
code.py: User-defined funcs and procs
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, value_t, scope_e
from _devbuild.gen.syntax_asdl import proc_sig, proc_sig_e

from core import error
from core.error import e_die
from core import state
from core import vm
from frontend import location

from typing import List, Dict, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import command, loc_t
    from _devbuild.gen.runtime_asdl import Proc
    from core import ui
    from osh import cmd_eval


class UserFunc(vm._Callable):
    """A user-defined function."""

    def __init__(self, name, node, mem, cmd_ev):
        # type: (str, command.Func, state.Mem, cmd_eval.CommandEvaluator) -> None
        self.name = name
        self.node = node
        self.cmd_ev = cmd_ev
        self.mem = mem

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t
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

        num_args = len(named_args)
        num_params = len(self.node.named_params)
        if num_args != num_params:
            raise error.TypeErrVerbose(
                "%s() expects %d named arguments but %d were given" %
                (self.name, num_params, num_args), blame_loc)

        # Push a new stack frame
        with state.ctx_FuncCall(self.cmd_ev.mem, self):

            num_args = len(self.node.pos_params)
            for i in xrange(0, num_args):
                pos_arg = pos_args[i]
                pos_param = self.node.pos_params[i]

                param_name = location.LName(pos_param.name)
                self.mem.SetValue(param_name, pos_arg, scope_e.LocalOnly)

            if self.node.rest_of_pos:
                other_args = value.List(pos_args[num_args:])
                param_name = location.LName(self.node.rest_of_pos.name)
                self.mem.SetValue(param_name, other_args, scope_e.LocalOnly)

            # TODO: pass named args

            try:
                self.cmd_ev._Execute(self.node.body)

                return value.Null  # implicit return
            except vm.ValueControlFlow as e:
                return e.value
            except vm.IntControlFlow as e:
                raise AssertionError('IntControlFlow in func')

        raise AssertionError('unreachable')


def BindProcArgs(proc, argv, arg0_loc, mem, errfmt):
    # type: (Proc, List[str], loc_t, state.Mem, ui.ErrorFormatter) -> int

    UP_sig = proc.sig
    if UP_sig.tag() != proc_sig_e.Closed:  # proc is-closed ()
        return 0

    sig = cast(proc_sig.Closed, UP_sig)

    n_args = len(argv)
    for i, p in enumerate(sig.word_params):

        # proc p(out Ref)
        is_out_param = (p.type is not None and p.type.name == 'Ref')

        param_name = p.name
        if i < n_args:
            arg_str = argv[i]

            # If we have myproc(p), and call it with myproc :arg, then bind
            # __p to 'arg'.  That is, the param has a prefix ADDED, and the arg
            # has a prefix REMOVED.
            #
            # This helps eliminate "nameref cycles".
            if is_out_param:
                param_name = '__' + param_name

                if not arg_str.startswith(':'):
                    # TODO: Point to the exact argument
                    e_die(
                        'Invalid argument %r.  Expected a name starting with :'
                        % arg_str)
                arg_str = arg_str[1:]

            val = value.Str(arg_str)  # type: value_t
        else:
            val = proc.defaults[i]
            if val is None:
                e_die("No value provided for param %r" % p.name, p.blame_tok)

        if is_out_param:
            flags = state.SetNameref
        else:
            flags = 0

        mem.SetValue(location.LName(param_name),
                     val,
                     scope_e.LocalOnly,
                     flags=flags)

    n_params = len(sig.word_params)
    if sig.rest_of_words:
        items = [value.Str(s) for s in argv[n_params:]]  # type: List[value_t]
        leftover = value.List(items)
        mem.SetValue(location.LName(sig.rest_of_words.name), leftover,
                     scope_e.LocalOnly)
    else:
        if n_args > n_params:
            # TODO: Raise an exception?
            errfmt.Print_(
                "proc %r expected %d arguments, but got %d" %
                (proc.name, n_params, n_args), arg0_loc)
            # This should be status 2 because it's like a usage error.
            return 2

    return 0
