from __future__ import print_function

from _devbuild.gen.runtime_asdl import scope_e
from _devbuild.gen.syntax_asdl import loc
from _devbuild.gen.value_asdl import (value, value_e)

from core import error
from core import state
from core import ui
from core import vm
from frontend import args
from frontend import flag_spec
from mycpp.mylib import log

from typing import Dict, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value
    from core import optview

_ = log


class IsMain(vm._Builtin):
    """is-main builtin.
    """

    def __init__(self, mem):
        # type: (state.Mem) -> None
        self.mem = mem

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        return 0 if self.mem.is_main else 1


class Module(vm._Builtin):
    """module builtin.

    module main || return
    """

    def __init__(self, modules, exec_opts, errfmt):
        # type: (Dict[str, bool], optview.Exec, ui.ErrorFormatter) -> None
        self.modules = modules
        self.exec_opts = exec_opts
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_spec.ParseCmdVal('module', cmd_val)
        name, _ = arg_r.ReadRequired2('requires a name')
        #log('modules %s', self.modules)
        if name in self.modules:
            # already defined
            if self.exec_opts.redefine_module():
                self.errfmt.PrintMessage('(interactive) Reloading module %r' %
                                         name)
                return 0
            else:
                return 1
        self.modules[name] = True
        return 0


class Use(vm._Builtin):
    """use bin, use dialect to control the 'first word'.

    Examples:
      use bin grep sed

      use dialect ninja   # I think it must be in a 'dialect' scope
      use dialect travis
    """

    def __init__(self, mem, errfmt):
        # type: (state.Mem, ui.ErrorFormatter) -> None
        self.mem = mem
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        arg_r = args.Reader(cmd_val.argv, locs=cmd_val.arg_locs)
        arg_r.Next()  # skip 'use'

        arg, arg_loc = arg_r.Peek2()
        if arg is None:
            raise error.Usage("expected 'bin' or 'dialect'", loc.Missing)
        arg_r.Next()

        if arg == 'dialect':
            expected, e_loc = arg_r.Peek2()
            if expected is None:
                raise error.Usage('expected dialect name', loc.Missing)

            UP_actual = self.mem.GetValue('_DIALECT', scope_e.Dynamic)
            if UP_actual.tag() == value_e.Str:
                actual = cast(value.Str, UP_actual).s
                if actual == expected:
                    return 0  # OK
                else:
                    self.errfmt.Print_('Expected dialect %r, got %r' %
                                       (expected, actual),
                                       blame_loc=e_loc)

                    return 1
            else:
                # Not printing expected value
                self.errfmt.Print_('Expected dialect %r' % expected,
                                   blame_loc=e_loc)
                return 1

        # 'use bin' can be used for static analysis.  Although could it also
        # simplify the SearchPath logic?  Maybe ensure that it is memoized?
        if arg == 'bin':
            rest = arg_r.Rest()
            for name in rest:
                log('bin %s', name)
            return 0

        raise error.Usage("expected 'bin' or 'dialect'", arg_loc)
