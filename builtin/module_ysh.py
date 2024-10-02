from __future__ import print_function

from _devbuild.gen.value_asdl import value, value_e, Obj
from core import state
from core import vm
from display import ui
from frontend import args
from frontend import flag_util
from mycpp.mylib import log

from typing import cast, Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value
    from core import optview

_ = log


class IsMain(vm._Builtin):
    """
    if is-main { echo hi }
    """

    def __init__(self, mem):
        # type: (state.Mem) -> None
        self.mem = mem

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        return 0 if self.mem.is_main else 1


class SourceGuard(vm._Builtin):
    """
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


class InvokeModule(vm._Builtin):
    """
    This is a builtin for the __invoke__ method of Obj my-module

    use my-module.ysh
    my-module my-proc
    """
    def __init__(self):
        # type: () -> None
        pass

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        arg_r = args.Reader(cmd_val.argv, locs=cmd_val.arg_locs)
        arg_r.Next()  # move past the builtin name

        invokable_name, _ = arg_r.ReadRequired2('requires a name')

        assert cmd_val.proc_args is not None
        assert cmd_val.proc_args.pos_args is not None

        # Now look for the invokable_name in self_val, which is the module
        self_val = cmd_val.proc_args.pos_args[0]

        # This is ensured by our arg passing
        assert self_val.tag() == value_e.Obj, self_val

        self_obj = cast(Obj, self_val)

        val = self_obj.d.get(invokable_name)

        # Similar to Procs.GetInvokable
        if val.tag() == value_e.Proc:
            proc = cast(value.Proc, val)

        # Recursively invokable ???
        proc, self_val2 = state._InvokableObj(val)
        if proc:
            #return proc, self_val
            pass

        # So now we look for a value.Proc
        # Or
        return 0
