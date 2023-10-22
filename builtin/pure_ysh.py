"""
builtin/pure_ysh.py - YSH builtins that don't do I/O.
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import (value, value_e, value_t, cmd_value,
                                        scope_e, lvalue)
from _devbuild.gen.syntax_asdl import loc
from core import error
from core import state
from core import vm
from frontend import flag_spec
from frontend import location
from frontend import typed_args
from mycpp import mylib
from mycpp.mylib import tagswitch

from typing import TYPE_CHECKING, cast, List, Tuple, Any

if TYPE_CHECKING:
    from core import ui
    from osh.cmd_eval import CommandEvaluator


class ctx_Shvar(object):
    """For shvar LANG=C _ESCAPER=posix-sh-word _DIALECT=ninja."""

    def __init__(self, mem, pairs):
        # type: (state.Mem, List[Tuple[str, str]]) -> None
        #log('pairs %s', pairs)
        self.mem = mem
        self.restore = []  # type: List[Tuple[lvalue.Named, value_t]]
        self._Push(pairs)

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self._Pop()

    # Note: _Push and _Pop are separate methods because the C++ translation
    # doesn't like when they are inline in __init__ and __exit__.
    def _Push(self, pairs):
        # type: (List[Tuple[str, str]]) -> None
        for name, s in pairs:
            lval = location.LName(name)
            # LocalOnly because we are only overwriting the current scope
            old_val = self.mem.GetValue(name, scope_e.LocalOnly)
            self.restore.append((lval, old_val))
            self.mem.SetNamed(lval, value.Str(s), scope_e.LocalOnly)

    def _Pop(self):
        # type: () -> None
        for lval, old_val in self.restore:
            if old_val.tag() == value_e.Undef:
                self.mem.Unset(lval, scope_e.LocalOnly)
            else:
                self.mem.SetNamed(lval, old_val, scope_e.LocalOnly)


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

        with ctx_Shvar(self.mem, pairs):
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
        arg, arg_r = flag_spec.ParseCmdVal('append',
                                           cmd_val,
                                           accept_typed_args=True)

        if not cmd_val.typed_args:  # eval (myblock)
            raise error.Usage('expected a List as a typed arg', loc.Missing)

        rd = typed_args.ReaderForProc(cmd_val)
        val = rd.PosValue()

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
