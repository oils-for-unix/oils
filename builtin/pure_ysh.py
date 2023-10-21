"""
builtin/pure_ysh.py - YSH builtins that don't do I/O.
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import (value, value_e, value_t, cmd_value)
from core import error
from core import vm
from frontend import flag_spec
from frontend import match
from mycpp.mylib import tagswitch

from typing import TYPE_CHECKING, cast, List

if TYPE_CHECKING:
    from core import ui
    from core import state


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
