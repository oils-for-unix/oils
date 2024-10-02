"""
builtin/pure_ysh.py - YSH builtins that don't do I/O.
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.syntax_asdl import command_t, loc, loc_t
from _devbuild.gen.value_asdl import value, value_e, value_t
from core import error
from core import state
from core import vm
from frontend import flag_util
from frontend import typed_args
from mycpp import mylib
from mycpp.mylib import tagswitch, NewDict

from typing import TYPE_CHECKING, cast, Any, Dict, List

if TYPE_CHECKING:
    from display import ui
    from osh.cmd_eval import CommandEvaluator


class Shvar(vm._Builtin):

    def __init__(self, mem, search_path, cmd_ev):
        # type: (state.Mem, state.SearchPath, CommandEvaluator) -> None
        self.mem = mem
        self.search_path = search_path  # to clear PATH
        self.cmd_ev = cmd_ev  # To run blocks

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('shvar',
                                         cmd_val,
                                         accept_typed_args=True)

        cmd = typed_args.OptionalBlock(cmd_val)
        if not cmd:
            # TODO: I think shvar LANG=C should just mutate
            # But should there be a whitelist?
            raise error.Usage('expected a block', loc.Missing)

        vars = NewDict()  # type: Dict[str, value_t]
        args, arg_locs = arg_r.Rest2()
        if len(args) == 0:
            raise error.Usage('Expected name=value', loc.Missing)

        for i, arg in enumerate(args):
            name, s = mylib.split_once(arg, '=')
            if s is None:
                raise error.Usage('Expected name=value', arg_locs[i])
            v = value.Str(s)  # type: value_t
            vars[name] = v

            # Important fix: shvar PATH='' { } must make all binaries invisible
            if name == 'PATH':
                self.search_path.ClearCache()

        with state.ctx_Eval(self.mem, None, None, vars):
            unused = self.cmd_ev.EvalCommand(cmd)

        return 0


class PushRegisters(vm._Builtin):

    def __init__(self, mem, cmd_ev):
        # type: (state.Mem, CommandEvaluator) -> None
        self.mem = mem
        self.cmd_ev = cmd_ev  # To run blocks

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('push-registers',
                                         cmd_val,
                                         accept_typed_args=True)

        cmd = typed_args.OptionalBlock(cmd_val)
        if not cmd:
            raise error.Usage('expected a block', loc.Missing)

        with state.ctx_Registers(self.mem):
            unused = self.cmd_ev.EvalCommand(cmd)

        # make it "SILENT" in terms of not mutating $?
        # TODO: Revisit this.  It might be better to provide the headless shell
        # with a way to SET $? instead.  Needs to be tested/prototyped.
        return self.mem.last_status[-1]


class Append(vm._Builtin):
    """Push word args onto an List.

    Not doing typed args since you can do

    :: mylist->append(42)
    """

    def __init__(self, mem, errfmt):
        # type: (state.Mem, ui.ErrorFormatter) -> None
        self.mem = mem
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        # This means we ignore -- , which is consistent
        _, arg_r = flag_util.ParseCmdVal('append',
                                         cmd_val,
                                         accept_typed_args=True)

        rd = typed_args.ReaderForProc(cmd_val)
        val = rd.PosValue()
        rd.Done()

        UP_val = val
        with tagswitch(val) as case:
            if case(value_e.BashArray):
                val = cast(value.BashArray, UP_val)
                val.strs.extend(arg_r.Rest())
            elif case(value_e.List):
                val = cast(value.List, UP_val)
                typed = [value.Str(s)
                         for s in arg_r.Rest()]  # type: List[value_t]
                val.items.extend(typed)
            else:
                raise error.TypeErr(val, 'expected List or BashArray',
                                    loc.Missing)

        return 0
