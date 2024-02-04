"""
builtin/pure_ysh.py - YSH builtins that don't do I/O.
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import (cmd_value, scope_e)
from _devbuild.gen.syntax_asdl import command_t, loc, loc_t
from _devbuild.gen.value_asdl import (value, value_e, value_t, LeftName)
from core import error
from core import state
from core import vm
from frontend import flag_spec
from frontend import location
from frontend import typed_args
from mycpp import mylib
from mycpp.mylib import tagswitch

from typing import TYPE_CHECKING, cast, Any, Dict, List, Tuple

if TYPE_CHECKING:
    from core import ui
    from osh.cmd_eval import CommandEvaluator


class ctx_Shvar(object):
    """For shvar LANG=C _ESCAPER=posix-sh-word _DIALECT=ninja."""

    def __init__(self, mem, pairs):
        # type: (state.Mem, List[Tuple[str, value_t]]) -> None
        #log('pairs %s', pairs)
        self.mem = mem
        self.restore = []  # type: List[Tuple[LeftName, value_t]]
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
        # type: (List[Tuple[str, value_t]]) -> None
        for name, v in pairs:
            lval = location.LName(name)
            # LocalOnly because we are only overwriting the current scope
            old_val = self.mem.GetValue(name, scope_e.LocalOnly)
            self.restore.append((lval, old_val))
            self.mem.SetNamed(lval, v, scope_e.LocalOnly)

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

        pairs = []  # type: List[Tuple[str, value_t]]
        args, arg_locs = arg_r.Rest2()
        if len(args) == 0:
            raise error.Usage('Expected name=value', loc.Missing)

        for i, arg in enumerate(args):
            name, s = mylib.split_once(arg, '=')
            if s is None:
                raise error.Usage('Expected name=value', arg_locs[i])
            v = value.Str(s)  # type: value_t
            pairs.append((name, v))

            # Important fix: shvar PATH='' { } must make all binaries invisible
            if name == 'PATH':
                self.search_path.ClearCache()

        with ctx_Shvar(self.mem, pairs):
            unused = self.cmd_ev.EvalCommand(cmd)

        return 0


class ctx_Context(object):
    """For ctx push (context) { ... }"""

    def __init__(self, mem, context):
        # type: (state.Mem, Dict[str, value_t]) -> None
        self.mem = mem
        self.mem.PushContextStack(context)

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        self.mem.PopContextStack()


class Ctx(vm._Builtin):

    def __init__(self, mem, cmd_ev):
        # type: (state.Mem, CommandEvaluator) -> None
        self.mem = mem
        self.cmd_ev = cmd_ev  # To run blocks

    def _GetContext(self):
        # type: () -> Dict[str, value_t]
        ctx = self.mem.GetContext()
        if ctx is None:
            raise error.Expr(
                "Could not find a context. Did you forget to 'ctx push'?",
                loc.Missing)
        return ctx

    def _Push(self, context, block):
        # type: (Dict[str, value_t], command_t) -> int
        with ctx_Context(self.mem, context):
            return self.cmd_ev.EvalCommand(block)

    def _Set(self, updates):
        # type: (Dict[str, value_t]) -> int
        ctx = self._GetContext()
        ctx.update(updates)
        return 0

    def _Emit(self, field, item, blame):
        # type: (str, value_t, loc_t) -> int
        ctx = self._GetContext()

        if field not in ctx:
            ctx[field] = value.List([])

        UP_arr = ctx[field]
        if UP_arr.tag() != value_e.List:
            raise error.TypeErr(
                UP_arr,
                "Expected the context item '%s' to be a List" % (field), blame)

        arr = cast(value.List, UP_arr)
        arr.items.append(item)

        return 0

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        rd = typed_args.ReaderForProc(cmd_val)
        _, arg_r = flag_spec.ParseCmdVal('ctx',
                                         cmd_val,
                                         accept_typed_args=True)

        verb, verb_loc = arg_r.ReadRequired2(
            'Expected a verb (push, set, emit)')

        if verb == "push":
            context = rd.PosDict()
            block = rd.PosCommand()
            rd.Done()
            arg_r.AtEnd()

            return self._Push(context, block)

        elif verb == "set":
            updates = rd.RestNamed()
            rd.Done()
            arg_r.AtEnd()

            return self._Set(updates)

        elif verb == "emit":
            field, field_loc = arg_r.ReadRequired2(
                "A target field is required")
            item = rd.PosValue()
            rd.Done()
            arg_r.AtEnd()

            return self._Emit(field, item, field_loc)

        else:
            raise error.Usage("Unknown verb '%s'" % verb, verb_loc)


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
