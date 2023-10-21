"""
builtin/pure_ysh.py - YSH builtins that don't do I/O.
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import (value, value_e, value_t, cmd_value)
from _devbuild.gen.syntax_asdl import loc
from core import error
from core import state
from core import vm
from frontend import flag_spec
from frontend import match
from frontend import typed_args
from mycpp import mylib
from mycpp.mylib import tagswitch

from typing import TYPE_CHECKING, cast, List, Tuple

if TYPE_CHECKING:
    from core import ui
    from osh.cmd_eval import CommandEvaluator


class Shvar(vm._Builtin):

    def __init__(self, mem, search_path, cmd_ev):
        # type: (state.Mem, state.SearchPath, CommandEvaluator) -> None
        self.mem = mem
        self.search_path = search_path  # to clear PATH
        self.cmd_ev = cmd_ev  # To run blocks

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_spec.ParseCmdVal('shvar',
                                         cmd_val,
                                         accept_typed_args=True)

        cmd = typed_args.OptionalCommand(cmd_val)
        if not cmd:
            # TODO: I think shvar LANG=C should just mutate
            # But should there be a whitelist?
            raise error.Usage('expected a block', loc.Missing)

        pairs = []  # type: List[Tuple[str, str]]
        args, arg_locs = arg_r.Rest2()
        if len(args) == 0:
            raise error.Usage('Expected name=value', loc.Missing)

        for i, arg in enumerate(args):
            name, s = mylib.split_once(arg, '=')
            if s is None:
                raise error.Usage('Expected name=value', arg_locs[i])
            pairs.append((name, s))

            # Important fix: shvar PATH='' { } must make all binaries invisible
            if name == 'PATH':
                self.search_path.ClearCache()

        with state.ctx_Shvar(self.mem, pairs):
            unused = self.cmd_ev.EvalCommand(cmd)

        return 0


class PushRegisters(vm._Builtin):

    def __init__(self, mem, cmd_ev):
        # type: (state.Mem, CommandEvaluator) -> None
        self.mem = mem
        self.cmd_ev = cmd_ev  # To run blocks

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_spec.ParseCmdVal('push-registers',
                                         cmd_val,
                                         accept_typed_args=True)

        cmd = typed_args.OptionalCommand(cmd_val)
        if not cmd:
            raise error.Usage('expected a block', loc.Missing)

        with state.ctx_Registers(self.mem):
            unused = self.cmd_ev.EvalCommand(cmd)

        # make it "SILENT" in terms of not mutating $?
        # TODO: Revisit this.  It might be better to provide the headless shell
        # with a way to SET $? instead.  Needs to be tested/prototyped.
        return self.mem.last_status[-1]


class Append(vm._Builtin):
    """Push args onto an array.

    Note: this could also be in builtins_pure.py?
    """

    def __init__(self, mem, errfmt):
        # type: (state.Mem, ui.ErrorFormatter) -> None
        self.mem = mem
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        arg, arg_r = flag_spec.ParseCmdVal('append', cmd_val)

        var_name, var_loc = arg_r.ReadRequired2('requires a variable name')

        if var_name.startswith(':'):  # optional : sigil
            var_name = var_name[1:]

        if not match.IsValidVarName(var_name):
            raise error.Usage('got invalid variable name %r' % var_name,
                              var_loc)

        val = self.mem.GetValue(var_name)

        # TODO: Get rid of value.BashArray
        ok = False
        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.BashArray):
                val = cast(value.BashArray, UP_val)
                val.strs.extend(arg_r.Rest())
                ok = True
            elif case(value_e.List):
                val = cast(value.List, UP_val)
                typed = [value.Str(s)
                         for s in arg_r.Rest()]  # type: List[value_t]
                val.items.extend(typed)
                ok = True

        if not ok:
            # consider exit code 3 like error.TypeErrVerbose?
            self.errfmt.Print_("%r isn't a List" % var_name, blame_loc=var_loc)
            return 1

        return 0
