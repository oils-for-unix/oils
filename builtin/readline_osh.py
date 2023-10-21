#!/usr/bin/env python2
"""
builtin_lib.py - Builtins that are bindings to libraries, e.g. GNU readline.
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.syntax_asdl import loc
from core.error import e_usage
from core import pyutil
from core import vm
from frontend import flag_spec
from mycpp import mylib

from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value
    from frontend.py_readline import Readline
    from core.ui import ErrorFormatter
    from core import shell


class Bind(vm._Builtin):
    """For :, true, false."""

    def __init__(self, readline, errfmt):
        # type: (Optional[Readline], ErrorFormatter) -> None
        self.readline = readline
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        self.errfmt.Print_("warning: bind isn't implemented",
                           blame_loc=cmd_val.arg_locs[0])
        return 1


class History(vm._Builtin):
    """Show interactive command history."""

    def __init__(
            self,
            readline,  # type: Optional[Readline]
            sh_files,  # type: shell.ShellFiles
            errfmt,  # type: ErrorFormatter
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
            e_usage("is disabled because Oil wasn't compiled with 'readline'",
                    loc.Missing)

        attrs, arg_r = flag_spec.ParseCmdVal('history', cmd_val)
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
        if arg.d >= 0:
            cmd_index = arg.d - 1

            try:
                readline.remove_history_item(cmd_index)
            except ValueError:
                e_usage("couldn't find item %d" % arg.d, loc.Missing)

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
