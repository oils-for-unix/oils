#!/usr/bin/env python2
"""
meta_ysh.py - Builtins for introspection
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import cmd_value
from core import error
from core.error import e_usage
from core import vm
from frontend import flag_spec
from frontend import match
from frontend import typed_args
from mycpp import mylib
from mycpp.mylib import log

_ = log

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from core import state
    from display import ui


class Shvm(vm._Builtin):
    """
    shvm cell x      - move pp cell x here
    shvm gc-stats    - like OILS_GC_STATS
    shvm guts (x+y)  - ASDL pretty printing
                     - similar to = x+y, but not stable

    Related:
      _vm->heapId(obj) - a heap ID that can be used to detect cycles for
                         serialization
    """

    def __init__(
            self,
            mem,  # type: state.Mem
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        self.mem = mem
        self.errfmt = errfmt
        self.stdout_ = mylib.Stdout()

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int

        arg, arg_r = flag_spec.ParseCmdVal('shvm', cmd_val)

        action, action_loc = arg_r.ReadRequired2(
            'expected an action (cell, gc-stats, guts)')

        if action == 'cell':
            argv, locs = arg_r.Rest2()

            status = 0
            for i, name in enumerate(argv):
                if name.startswith(':'):
                    name = name[1:]

                if not match.IsValidVarName(name):
                    raise error.Usage('got invalid variable name %r' % name,
                                      locs[i])

                cell = self.mem.GetCell(name)
                if cell is None:
                    self.errfmt.Print_("Couldn't find a variable named %r" %
                                       name,
                                       blame_loc=locs[i])
                    status = 1
                else:
                    self.stdout_.write('%s = ' % name)
                    if mylib.PYTHON:
                        cell.PrettyPrint()  # may be color

                    self.stdout_.write('\n')

        elif action == 'gc-stats':
            # mylib.PrintGcStats()
            print('TODO')
            status = 0

        elif action == 'guts':
            # Print the value
            print('TODO')

            if cmd_val.typed_args:  # eval (myblock)
                rd = typed_args.ReaderForProc(cmd_val)
                val = rd.PosValue()
                rd.Done()
                if mylib.PYTHON:
                    print(val)

            status = 0

        else:
            e_usage('got invalid action %r' % action, action_loc)

        return status
