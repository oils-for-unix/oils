#!/usr/bin/env python2
"""
readline_osh.py - Builtins that are dependent on GNU readline.
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.syntax_asdl import loc
from _devbuild.gen.value_asdl import value_e
from core import pyutil
from core import vm
from core.error import e_usage
from frontend import flag_util
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import log
from osh import cmd_eval

from typing import Optional, Tuple, Any, TYPE_CHECKING
if TYPE_CHECKING:
    from builtin.meta_oils import Eval
    from frontend.py_readline import Readline
    from core import sh_init
    from core.state import Mem
    from display import ui

_ = log


class ctx_Keymap(object):

    def __init__(self, readline, keymap_name=None):
        # type: (Readline, Optional[str]) -> None
        self.readline = readline
        self.orig_keymap_name = keymap_name

    def __enter__(self):
        # type: () -> None
        if self.orig_keymap_name is not None:
            self.readline.use_temp_keymap(self.orig_keymap_name)

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        if self.orig_keymap_name is not None:
            self.readline.restore_orig_keymap()


class BindXCallback(object):
    """A callable we pass to readline for executing shell commands."""

    def __init__(self, eval):
        # type: (Eval) -> None
        self.eval = eval

    def __call__(self, cmd, line_buffer, point):
        # type: (str, str, int) -> Tuple[int, str, str]
        """Execute a shell command through the evaluator.

        Args:
          cmd: The shell command to execute
          line_buffer: The current line buffer
          point: The current cursor position
        """
        print("Setting READLINE_LINE to: %s" % line_buffer)
        print("Setting READLINE_POINT to: %s" % point)
        print("Executing cmd: %s" % cmd)

        # TODO: add READLINE_* env vars later
        # assert isinstance(line_buffer, str)
        # self.mem.SetNamed(location.LName("READLINE_LINE"),
        #                  value.Str(line_buffer),
        #                  scope_e.GlobalOnly,
        #                  flags=SetExport)

        # TODO: refactor out shared code from Eval, cache parse tree?

        cmd_val = cmd_eval.MakeBuiltinArgv([cmd])
        status = self.eval.Run(cmd_val)

        return (status, line_buffer, str(point))


class Bind(vm._Builtin):
    """Interactive interface to readline bindings"""

    def __init__(self, readline, errfmt, mem, bindx_cb):
        # type: (Optional[Readline], ui.ErrorFormatter, Mem, BindXCallback) -> None
        self.readline = readline
        self.errfmt = errfmt
        self.mem = mem
        self.exclusive_flags = ["q", "u", "r", "x", "f"]
        self.bindx_cb = bindx_cb
        if self.readline:
            self.readline.set_bind_shell_command_hook(self.bindx_cb)

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        readline = self.readline

        if not readline:
            e_usage("is disabled because Oils wasn't compiled with 'readline'",
                    loc.Missing)

        attrs, arg_r = flag_util.ParseCmdVal('bind', cmd_val)

        # print("attrs:\n", attrs)
        # print("attrs.attrs:\n", attrs.attrs)
        # print("attrs.attrs[m]:\n", attrs.attrs["m"])
        # print("type(attrs.attrs[m]):\n", type(attrs.attrs["m"]))
        # print("type(attrs.attrs[m]):\n", type(attrs.attrs["m"]))
        # print("attrs.attrs[m].tag() :\n", attrs.attrs["m"].tag())
        # print("attrs.attrs[m].tag() == value_e.Undef:\n", attrs.attrs["m"].tag() == value_e.Undef)
        # print(arg_r)
        # print("Reader argv=%s locs=%s n=%i i=%i" % (arg_r.argv, str(arg_r.locs), arg_r.n, arg_r.i))

        # Check mutually-exclusive flags and non-flag args
        found = False
        for flag in self.exclusive_flags:
            if (flag in attrs.attrs and
                    attrs.attrs[flag].tag() != value_e.Undef):
                # print("\tFound flag: {0} with tag: {1}".format(flag, attrs.attrs[flag].tag()))
                if found:
                    self.errfmt.Print_(
                        "error: Can only use one of the following flags at a time: -"
                        + ", -".join(self.exclusive_flags),
                        blame_loc=cmd_val.arg_locs[0])
                    return 1
                else:
                    found = True
        if found and not arg_r.AtEnd():
            self.errfmt.Print_(
                "error: Too many arguments. Also, you cannot mix normal bindings with the following flags: -"
                + ", -".join(self.exclusive_flags),
                blame_loc=cmd_val.arg_locs[0])
            return 1

        arg = arg_types.bind(attrs.attrs)
        # print("arg:\n", arg)
        # print("dir(arg):\n", dir(arg))
        # for prop in dir(arg):
        #     if not prop.startswith('__'):
        #         value = getattr(arg, prop)
        #         print("Property: {0}, Value: {1}".format(prop, value))
        # print("arg.m:\n", arg.m)

        try:
            with ctx_Keymap(readline, arg.m):  # Replicates bind's -m behavior

                # This gauntlet of ifs is meant to replicate bash behavior, in case we
                # need to relax the mutual exclusion of flags like bash does

                # List names of functions
                if arg.l:
                    readline.list_funmap_names()

                # Print function names and bindings
                if arg.p:
                    readline.function_dumper(True)  # reusable as input
                if arg.P:
                    readline.function_dumper(False)

                # Print macros
                if arg.s:
                    readline.macro_dumper(True)  # reusable as input
                if arg.S:
                    readline.macro_dumper(False)

                # Print readline variable names
                if arg.v:
                    readline.variable_dumper(True)
                if arg.V:
                    readline.variable_dumper(False)

                if arg.f is not None:
                    readline.read_init_file(arg.f)

                if arg.q is not None:
                    readline.query_bindings(arg.q)

                if arg.u is not None:
                    readline.unbind_rl_function(arg.u)

                if arg.r is not None:
                    readline.unbind_keyseq(arg.r)

                if arg.x is not None:
                    self._BindShellCmd(arg.x)

                if arg.X:
                    readline.print_shell_cmd_map()

                bindings, arg_locs = arg_r.Rest2()
                #log('bindings %d locs %d', len(arg_r.argv), len(arg_r.locs))

                for i, binding in enumerate(bindings):
                    try:
                        #log("Binding %s (%d)", binding, i)
                        #log("Arg loc %s (%d)", arg_locs[i], i)
                        readline.parse_and_bind(binding)
                    except ValueError as e:
                        msg = e.message  # type: str
                        self.errfmt.Print_("bind error: %s" % msg, arg_locs[i])
                        return 1

        except ValueError as e:
            # only print out the exception message if non-empty
            # some bash bind errors return non-zero, but print to stdout
            # temp var to work around mycpp runtime limitation
            msg2 = e.message  # type: str
            if msg2 is not None and len(msg2) > 0:
                self.errfmt.Print_("bind error: %s" % msg2, loc.Missing)
            return 1

        return 0

    def _BindShellCmd(self, bindseq):
        # type: (str) -> None

        # print("bind -x '%s'" % bindseq)

        # print("hex bindseq: %s" % bindseq.join('%02x' % ord(c) for c in s))
        # print("stripped bindseq: %s" % bindseq.strip())
        cmdseq_split = bindseq.strip().split(":", 1)
        if len(cmdseq_split) != 2:
            raise ValueError("%s: missing colon separator" % bindseq)

        # Below checks prevent need to do so in C, but also ensure rl_generic_bind
        # will not try to incorrectly xfree `cmd`/`data`, which doesn't belong to it
        keyseq = cmdseq_split[0].rstrip()
        if len(keyseq) <= 2:
            raise ValueError("%s: empty/invalid key sequence" % keyseq)
        if keyseq[0] != '"' or keyseq[-1] != '"':
            raise ValueError(
                "%s: missing double-quotes around the key sequence" % keyseq)
        keyseq = keyseq[1:-1]

        cmd = cmdseq_split[1]

        self.readline.bind_shell_command(keyseq, cmd)


class History(vm._Builtin):
    """Show interactive command history."""

    def __init__(
            self,
            readline,  # type: Optional[Readline]
            sh_files,  # type: sh_init.ShellFiles
            errfmt,  # type: ui.ErrorFormatter
            f,  # type: mylib.Writer
    ):
        # type: (...) -> None
        self.readline = readline
        self.sh_files = sh_files
        self.errfmt = errfmt
        self.f = f  # this hook is for unit testing only

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        # NOTE: This builtin doesn't do anything in non-interactive mode in bash?
        # It silently exits zero.
        # zsh -c 'history' produces an error.
        readline = self.readline
        if not readline:
            e_usage("is disabled because Oils wasn't compiled with 'readline'",
                    loc.Missing)

        attrs, arg_r = flag_util.ParseCmdVal('history', cmd_val)
        arg = arg_types.history(attrs.attrs)

        # Clear all history
        if arg.c:
            readline.clear_history()
            return 0

        if arg.a:
            hist_file = self.sh_files.HistoryFile()
            if hist_file is None:
                return 1

            try:
                readline.write_history_file(hist_file)
            except (IOError, OSError) as e:
                self.errfmt.Print_(
                    'Error writing HISTFILE %r: %s' %
                    (hist_file, pyutil.strerror(e)), loc.Missing)
                return 1

            return 0

        if arg.r:
            hist_file = self.sh_files.HistoryFile()
            if hist_file is None:
                return 1

            try:
                readline.read_history_file(hist_file)
            except (IOError, OSError) as e:
                self.errfmt.Print_(
                    'Error reading HISTFILE %r: %s' %
                    (hist_file, pyutil.strerror(e)), loc.Missing)
                return 1

            return 0

        # Delete history entry by id number
        arg_d = mops.BigTruncate(arg.d)
        if arg_d >= 0:
            cmd_index = arg_d - 1

            try:
                readline.remove_history_item(cmd_index)
            except ValueError:
                e_usage("couldn't find item %d" % arg_d, loc.Missing)

            return 0

        # Returns 0 items in non-interactive mode?
        num_items = readline.get_current_history_length()
        #log('len = %d', num_items)

        num_arg, num_arg_loc = arg_r.Peek2()

        if num_arg is None:
            start_index = 1
        else:
            try:
                num_to_show = int(num_arg)
            except ValueError:
                e_usage('got invalid argument %r' % num_arg, num_arg_loc)
            start_index = max(1, num_items + 1 - num_to_show)

        arg_r.Next()
        if not arg_r.AtEnd():
            e_usage('got too many arguments', loc.Missing)

        # TODO:
        # - Exclude lines that don't parse from the history!  bash and zsh don't do
        # that.
        # - Consolidate multiline commands.

        for i in xrange(start_index, num_items + 1):  # 1-based index
            item = readline.get_history_item(i)
            self.f.write('%5d  %s\n' % (i, item))
        return 0
