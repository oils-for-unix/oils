#!/usr/bin/env python2
"""
builtin_oil.py - Oil builtins.

See rfc/0024-oil-builtins.md for notes.

env: Should be in builtin_compat.py?

It's sort of like xargs too.
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import (value, value_e, value_t, ProcValue,
                                        cmd_value)
from _devbuild.gen.syntax_asdl import command_e, BraceGroup
from core import error
from core.error import e_usage
from core import state
from core import vm
from frontend import flag_spec
from frontend import match
from mycpp import mylib
from mycpp.mylib import log, tagswitch, Stdout
from data_lang import qsn
from data_lang import j8

from typing import TYPE_CHECKING, cast, Dict, List
if TYPE_CHECKING:
    from core.alloc import Arena
    from core.ui import ErrorFormatter

_ = log


class _Builtin(vm._Builtin):

    def __init__(self, mem, errfmt):
        # type: (state.Mem, ErrorFormatter) -> None
        self.mem = mem
        self.errfmt = errfmt


class Pp(_Builtin):
    """Given a list of variable names, print their values.

    'pp cell a' is a lot easier to type than 'argv.py "${a[@]}"'.
    """

    def __init__(self, mem, errfmt, procs, arena):
        # type: (state.Mem, ErrorFormatter, Dict[str, ProcValue], Arena) -> None
        _Builtin.__init__(self, mem, errfmt)
        self.procs = procs
        self.arena = arena
        self.stdout_ = Stdout()

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        arg, arg_r = flag_spec.ParseCmdVal('pp', cmd_val)

        action, action_loc = arg_r.ReadRequired2(
            'expected an action (proc, cell, etc.)')

        # Actions that print unstable formats start with '.'
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

        elif action == 'proc':
            names, locs = arg_r.Rest2()
            if len(names):
                for i, name in enumerate(names):
                    node = self.procs.get(name)
                    if node is None:
                        self.errfmt.Print_('Invalid proc %r' % name,
                                           blame_loc=locs[i])
                        return 1
            else:
                names = sorted(self.procs)

            # QTSV header
            print('proc_name\tdoc_comment')
            for name in names:
                proc = self.procs[name]  # must exist
                #log('Proc %s', proc)
                body = proc.body

                # TODO: not just command.ShFunction, but command.Proc!
                doc = ''
                if body.tag() == command_e.BraceGroup:
                    bgroup = cast(BraceGroup, body)
                    if bgroup.doc_token:
                        token = bgroup.doc_token
                        # 1 to remove leading space
                        doc = token.line.content[token.col + 1:token.col +
                                                 token.length]

                # No limits on proc names
                print('%s\t%s' %
                      (qsn.maybe_encode(name), qsn.maybe_encode(doc)))

            status = 0

        else:
            e_usage('got invalid action %r' % action, action_loc)

        return status


class Append(_Builtin):
    """Push args onto an array.

    Note: this could also be in builtins_pure.py?
    """

    def __init__(self, mem, errfmt):
        # type: (state.Mem, ErrorFormatter) -> None
        _Builtin.__init__(self, mem, errfmt)

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


class Write(_Builtin):
    """
  write -- @strs
  write --sep ' ' --end '' -- @strs
  write -n -- @
  write --qsn -- @strs   # argv serialization
  write --qsn --sep $'\t' -- @strs   # this is like QTSV
  """

    def __init__(self, mem, errfmt):
        # type: (state.Mem, ErrorFormatter) -> None
        _Builtin.__init__(self, mem, errfmt)
        self.stdout_ = Stdout()
        self.printer = j8.Printer(0)

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_spec.ParseCmdVal('write', cmd_val)
        arg = arg_types.write(attrs.attrs)
        #print(arg)

        if arg.unicode == 'raw':
            bit8_display = qsn.BIT8_UTF8
        elif arg.unicode == 'u':
            bit8_display = qsn.BIT8_U_ESCAPE
        elif arg.unicode == 'x':
            bit8_display = qsn.BIT8_X_ESCAPE
        else:
            raise AssertionError()

        i = 0
        while not arg_r.AtEnd():
            if i != 0:
                self.stdout_.write(arg.sep)
            s = arg_r.Peek()

            if arg.j8:
                buf = mylib.BufWriter()
                self.printer.Print(value.Str(s), buf, -1)
                s = buf.getvalue()

            elif arg.qsn:
                s = qsn.maybe_encode(s, bit8_display)

            self.stdout_.write(s)

            arg_r.Next()
            i += 1

        if arg.n:
            pass
        elif len(arg.end):
            self.stdout_.write(arg.end)

        return 0
