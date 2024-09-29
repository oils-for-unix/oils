from __future__ import print_function

from core import state
from display import ui
from core import vm
from frontend import flag_util
from mycpp.mylib import log

from typing import Dict, TYPE_CHECKING
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


class SourceGuard(vm._Builtin):
    """source-guard builtin.

    source-guard main || return
    """

    def __init__(self, guards, exec_opts, errfmt):
        # type: (Dict[str, bool], optview.Exec, ui.ErrorFormatter) -> None
        self.guards = guards
        self.exec_opts = exec_opts
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('source-guard', cmd_val)
        name, _ = arg_r.ReadRequired2('requires a name')
        #log('guards %s', self.guards)
        if name in self.guards:
            # already defined
            if self.exec_opts.redefine_module():
                self.errfmt.PrintMessage(
                    '(interactive) Reloading source file %r' % name)
                return 0
            else:
                return 1
        self.guards[name] = True
        return 0
