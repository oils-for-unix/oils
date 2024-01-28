#!/usr/bin/env python2
"""
builtin/io_ysh.py - YSH builtins that perform I/O
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.syntax_asdl import command_e, BraceGroup, loc
from _devbuild.gen.value_asdl import value
from asdl import format as fmt
from core import error
from core.error import e_usage
from core import state
from core import ui
from core import vm
from data_lang import qsn
from data_lang import j8
from frontend import flag_spec
from frontend import match
from frontend import typed_args
from mycpp import mylib
from mycpp.mylib import log

from typing import TYPE_CHECKING, cast, Dict
if TYPE_CHECKING:
    from core.alloc import Arena
    from core.ui import ErrorFormatter
    from osh import cmd_eval

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
        # type: (state.Mem, ErrorFormatter, Dict[str, value.Proc], Arena) -> None
        _Builtin.__init__(self, mem, errfmt)
        self.procs = procs
        self.arena = arena
        self.stdout_ = mylib.Stdout()
        self.j8print = j8.Printer()

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        arg, arg_r = flag_spec.ParseCmdVal('pp',
                                           cmd_val,
                                           accept_typed_args=True)

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
                    pretty_f = fmt.DetectConsoleOutput(self.stdout_)
                    fmt.PrintTree(cell.PrettyTree(), pretty_f)
                    self.stdout_.write('\n')

        elif action == 'asdl':
            # TODO: could be pp asdl (x, y, z)
            rd = typed_args.ReaderForProc(cmd_val)
            val = rd.PosValue()
            rd.Done()

            tree = val.PrettyTree()

            # TODO: ASDL should print the IDs.  And then they will be
            # line-wrapped.
            # The IDs should also be used to detect cycles, and omit values
            # already printed.
            #id_str = vm.ValueIdString(val)
            #f.write('    <%s%s>\n' % (ysh_type, id_str))

            pretty_f = fmt.DetectConsoleOutput(self.stdout_)
            fmt.PrintTree(tree, pretty_f)
            self.stdout_.write('\n')

            status = 0

        elif action == 'line':
            # Print format for unit tests

            # TODO: could be pp asdl (x, y, z)
            rd = typed_args.ReaderForProc(cmd_val)
            val = rd.PosValue()
            rd.Done()

            ysh_type = ui.ValType(val)
            self.stdout_.write('(%s)   ' % ysh_type)

            self.j8print.PrintLine(val, self.stdout_)

            status = 0

        elif action == 'gc-stats':
            print('TODO')
            status = 0

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


class Write(_Builtin):
    """
    write -- @strs
    write --sep ' ' --end '' -- @strs
    write -n -- @
    write --j8 -- @strs   # argv serialization
    write --j8 --sep $'\t' -- @strs   # this is like TSV8
    """

    def __init__(self, mem, errfmt):
        # type: (state.Mem, ErrorFormatter) -> None
        _Builtin.__init__(self, mem, errfmt)
        self.stdout_ = mylib.Stdout()
        self.j8print = j8.Printer()

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

            if arg.json:
                s = self.j8print.MaybeEncodeJsonString(s)

            elif arg.j8:
                s = self.j8print.MaybeEncodeString(s)

            # TODO: remove this
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


class Fopen(vm._Builtin):
    """fopen does nothing but run a block.

    It's used solely for its redirects.
        fopen >out.txt { echo hi }

    It's a subset of eval
        eval >out.txt { echo hi }
    """

    def __init__(self, mem, cmd_ev):
        # type: (state.Mem, cmd_eval.CommandEvaluator) -> None
        self.mem = mem
        self.cmd_ev = cmd_ev  # To run blocks

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_spec.ParseCmdVal('fopen',
                                         cmd_val,
                                         accept_typed_args=True)

        cmd = typed_args.OptionalCommand(cmd_val)
        if not cmd:
            raise error.Usage('expected a block', loc.Missing)

        unused = self.cmd_ev.EvalCommand(cmd)
        return 0
