from __future__ import print_function

from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.value_asdl import value, value_e
from core import error
from core import state
from core import vm
from display import ui
from frontend import args
from frontend import flag_util
from mycpp.mylib import log

from typing import cast, Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from core import optview
    from osh import cmd_eval

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

    def __init__(self, cmd_ev, errfmt):
        # type: (cmd_eval.CommandEvaluator, ui.ErrorFormatter) -> None
        self.cmd_ev = cmd_ev
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        arg_r = args.Reader(cmd_val.argv, locs=cmd_val.arg_locs)
        arg_r.Next()  # move past the module name

        invokable_name, invokable_loc = arg_r.Peek2()
        if invokable_name is None:
            raise error.Usage(
                'module must be invoked with a proc name argument',
                cmd_val.arg_locs[0])

        argv, locs = arg_r.Rest2()  # include proc name

        self_obj = cmd_val.self_obj
        assert self_obj is not None  # wouldn't have been called

        val = self_obj.d.get(invokable_name)

        #log('invokable_name %r', invokable_name)
        #log('argv %r', argv)

        # Similar to Procs::GetInvokable() - Proc or Obj

        if val is not None:
            # OK this is a proc 'log', so we found self, so now just invoke it
            # with the args.  No self obj!
            cmd_val2 = cmd_value.Argv(argv, locs, cmd_val.is_last_cmd, None,
                                      cmd_val.proc_args)

            if val.tag() == value_e.Proc:
                proc = cast(value.Proc, val)
                #log('proc %r', proc.name)

                status = self.cmd_ev.RunProc(proc, cmd_val2)
                return status

            # The module itself is an invokable Obj, but it also CONTAINS an
            # invokable Obj
            proc_val, self_obj2 = state.ValueIsInvokableObj(val)
            cmd_val2.self_obj = self_obj2
            if proc_val:
                # must be user-defined proc, not builtin
                if proc_val.tag() != value_e.Proc:
                    raise error.TypeErr(proc_val, "expected user-defined proc",
                                        invokable_loc)
                proc = cast(value.Proc, proc_val)

                status = self.cmd_ev.RunProc(proc, cmd_val2)
                return status

        # Any other type of value
        raise error.Usage(
            "module doesn't contain invokable %r" % invokable_name,
            invokable_loc)
