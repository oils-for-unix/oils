#!/usr/bin/env python2
"""
builtin/io_ysh.py - YSH builtins that perform I/O
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.syntax_asdl import command_e, BraceGroup
from _devbuild.gen.value_asdl import value, value_e
from asdl import format as fmt
from core import error
from core.error import e_usage
from core import state
from display import ui
from core import vm
from data_lang import j8
from frontend import flag_util
from frontend import match
from frontend import typed_args
from mycpp import mylib
from mycpp.mylib import log, iteritems

from typing import TYPE_CHECKING, cast
if TYPE_CHECKING:
    from core.alloc import Arena
    from osh import cmd_eval
    from ysh import expr_eval

_ = log


class _Builtin(vm._Builtin):

    def __init__(self, mem, errfmt):
        # type: (state.Mem, ui.ErrorFormatter) -> None
        self.mem = mem
        self.errfmt = errfmt


class Pp(_Builtin):
    """Given a list of variable names, print their values.

    'pp cell a' is a lot easier to type than 'argv.py "${a[@]}"'.
    """

    def __init__(
            self,
            expr_ev,  # type: expr_eval.ExprEvaluator
            mem,  # type: state.Mem
            errfmt,  # type: ui.ErrorFormatter
            procs,  # type: state.Procs
            arena,  # type: Arena
    ):
        # type: (...) -> None
        _Builtin.__init__(self, mem, errfmt)
        self.expr_ev = expr_ev
        self.procs = procs
        self.arena = arena
        self.stdout_ = mylib.Stdout()

    def _PrettyPrint(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        rd = typed_args.ReaderForProc(cmd_val)
        val = rd.PosValue()
        rd.Done()

        blame_tok = rd.LeftParenToken()

        # Show it with location
        # It looks like
        #   pp (42)
        #      ^
        # [ stdin ]:5: (Int)   42
        # We could also print with ! or -^-

        self.stdout_.write('\n')
        excerpt, prefix = ui.CodeExcerptAndPrefix(blame_tok)
        self.stdout_.write(excerpt)
        ui.PrettyPrintValue(prefix, val, self.stdout_)

        return 0

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        arg, arg_r = flag_util.ParseCmdVal('pp',
                                           cmd_val,
                                           accept_typed_args=True)

        action, action_loc = arg_r.Peek2()

        # Special cases
        # pp (x) quotes its code location, can also be pp [x]
        if action is None:
            return self._PrettyPrint(cmd_val)

        arg_r.Next()

        if action == 'value':
            # pp value (x) prints in the same way that '= x' does
            rd = typed_args.ReaderForProc(cmd_val)
            val = rd.PosValue()
            rd.Done()

            ui.PrettyPrintValue('', val, self.stdout_)
            return 0

        if action == 'asdl_':
            # TODO: could be pp asdl_ (x, y, z)
            rd = typed_args.ReaderForProc(cmd_val)
            val = rd.PosValue()
            rd.Done()

            tree = val.PrettyTree()
            #tree = val.AbbreviatedTree()  # I used this to test cycle detection

            # TODO: ASDL should print the IDs.  And then they will be
            # line-wrapped.
            # The IDs should also be used to detect cycles, and omit values
            # already printed.
            #id_str = vm.ValueIdString(val)
            #f.write('    <%s%s>\n' % (ysh_type, id_str))

            pretty_f = fmt.DetectConsoleOutput(self.stdout_)
            fmt.PrintTree(tree, pretty_f)
            self.stdout_.write('\n')

            return 0

        if action == 'test_':  # Print format for spec tests
            # TODO: could be pp test_ (x, y, z)
            rd = typed_args.ReaderForProc(cmd_val)
            val = rd.PosValue()
            rd.Done()

            if ui.TypeNotPrinted(val):
                ysh_type = ui.ValType(val)
                self.stdout_.write('(%s)   ' % ysh_type)

            j8.PrintLine(val, self.stdout_)

            return 0

        if action == 'cell_':  # Format may change
            argv, locs = arg_r.Rest2()

            status = 0
            for i, name in enumerate(argv):

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
            return status

        if action == 'stacks_':  # Format may change
            if mylib.PYTHON:
                var_stack, argv_stack, unused = self.mem.Dump()
                print(var_stack)
                print('===')
                print(argv_stack)
            if 0:
                var_stack = self.mem.var_stack
                for i, frame in enumerate(var_stack):
                    print('=== Frame %d' % i)
                    for name, cell in iteritems(frame):
                        print('%s = %s' % (name, cell))

            return 0

        if action == 'frame_vars_':  # Print names in current frame, for testing
            top = self.mem.var_stack[-1]
            print('    [frame_vars_] %s' % ' '.join(top.keys()))
            return 0

        if action == 'gc-stats_':
            print('TODO')
            return 0

        if action == 'proc':
            names, locs = arg_r.Rest2()
            if len(names):
                for i, name in enumerate(names):
                    node, _ = self.procs.GetInvokable(name)
                    if node is None:
                        self.errfmt.Print_('Invalid proc %r' % name,
                                           blame_loc=locs[i])
                        return 1
            else:
                names = self.procs.InvokableNames()

            # TSV8 header
            print('proc_name\tdoc_comment')
            for name in names:
                proc_val, _ = self.procs.GetInvokable(name)  # must exist
                if proc_val.tag() != value_e.Proc:
                    continue  # can't be value.BuiltinProc
                user_proc = cast(value.Proc, proc_val)

                body = user_proc.body

                # TODO: not just command.ShFunction, but command.Proc!
                doc = ''
                if body.tag() == command_e.BraceGroup:
                    bgroup = cast(BraceGroup, body)
                    if bgroup.doc_token:
                        token = bgroup.doc_token
                        # 1 to remove leading space
                        doc = token.line.content[token.col + 1:token.col +
                                                 token.length]

                # Note: these should be attributes on value.Proc
                buf = mylib.BufWriter()
                j8.EncodeString(name, buf, unquoted_ok=True)
                buf.write('\t')
                j8.EncodeString(doc, buf, unquoted_ok=True)
                print(buf.getvalue())

            return 0

        e_usage('got invalid action %r' % action, action_loc)
        #return status


class Write(_Builtin):
    """
    write -- @strs
    write --sep ' ' --end '' -- @strs
    write -n -- @
    write --j8 -- @strs   # argv serialization
    write --j8 --sep $'\t' -- @strs   # this is like TSV8
    """

    def __init__(self, mem, errfmt):
        # type: (state.Mem, ui.ErrorFormatter) -> None
        _Builtin.__init__(self, mem, errfmt)
        self.stdout_ = mylib.Stdout()

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('write', cmd_val)
        arg = arg_types.write(attrs.attrs)
        #print(arg)

        i = 0
        while not arg_r.AtEnd():
            if i != 0:
                self.stdout_.write(arg.sep)
            s = arg_r.Peek()

            if arg.json:
                s = j8.MaybeEncodeJsonString(s)

            elif arg.j8:
                s = j8.MaybeEncodeString(s)

            self.stdout_.write(s)

            arg_r.Next()
            i += 1

        if arg.n:
            pass
        elif len(arg.end):
            self.stdout_.write(arg.end)

        return 0


class RunBlock(vm._Builtin):
    """Used for 'redir' builtin

    It's used solely for its redirects.
        redir >out.txt { echo hi }
    """

    def __init__(self, mem, cmd_ev):
        # type: (state.Mem, cmd_eval.CommandEvaluator) -> None
        self.mem = mem
        self.cmd_ev = cmd_ev  # To run blocks

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('redir',
                                         cmd_val,
                                         accept_typed_args=True)

        cmd_frag = typed_args.RequiredBlockAsFrag(cmd_val)
        unused = self.cmd_ev.EvalCommandFrag(cmd_frag)
        return 0
