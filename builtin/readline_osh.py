#!/usr/bin/env python2
"""
readline_osh.py - Builtins that are dependent on GNU readline.
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value, scope_e
from _devbuild.gen.syntax_asdl import loc
from _devbuild.gen.value_asdl import value, value_e, value_str
from core import pyutil, state, vm
from core.error import e_usage
from frontend import flag_util, location
from mycpp import mops
from mycpp import mylib
from mycpp.mylib import log, tagswitch
from osh import cmd_eval

from typing import Optional, Tuple, Any, Dict, cast, TYPE_CHECKING
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


class ctx_EnvVars(object):
    """
    Context manager for temporarily setting environment variables.
    
    Ignores any pre-existing values for the env vars.
    """

    def __init__(self, mem, env_vars):
        # type: (Mem, Dict[str, str]) -> None
        self.mem = mem
        self.env_vars = env_vars

    def __enter__(self):
        # type: () -> None
        for name, val in self.env_vars.items():
            state.ExportGlobalString(self.mem, name, val)

    def __exit__(self, type, value, traceback):
        # type: (Any, Any, Any) -> None
        # Clean up env vars after command execution
        for name in self.env_vars:
            self.mem.Unset(location.LName(name), scope_e.GlobalOnly)


class BindXCallback(object):
    """A callable we pass to readline for executing shell commands."""

    def __init__(self, eval, mem, errfmt):
        # type: (Eval, Mem, ui.ErrorFormatter) -> None
        self.eval = eval
        self.mem = mem
        self.errfmt = errfmt

    def __call__(self, cmd, line_buffer, point):
        # type: (str, str, int) -> Tuple[int, str, int]
        """Execute a shell command through the evaluator.

        Args:
          cmd: The shell command to execute
          line_buffer: The current line buffer
          point: The current cursor position
        """

        with ctx_EnvVars(self.mem, {
                'READLINE_LINE': line_buffer,
                'READLINE_POINT': str(point)
        }):
            # TODO: refactor out shared code from Eval, cache parse tree?

            cmd_val = cmd_eval.MakeBuiltinArgv([cmd])
            status = self.eval.Run(cmd_val)

            # Retrieve READLINE_* env vars to check for changes
            readline_line = self._get_rl_env_var('READLINE_LINE')
            readline_point = self._get_rl_env_var('READLINE_POINT')

            post_line_buffer = readline_line if readline_line is not None else line_buffer
            post_point = int(
                readline_point) if readline_point is not None else point

            return (status, post_line_buffer, post_point)

    def _get_rl_env_var(self, envvar_name):
        # type: (str) -> Optional[str]
        """Retrieve the value of an env var, return None if undefined"""

        envvar_val = self.mem.GetValue(envvar_name, scope_e.GlobalOnly)
        with tagswitch(envvar_val) as case:
            if case(value_e.Str):
                return cast(value.Str, envvar_val).s
            elif case(value_e.Undef):
                return None
            else:
                # bash has silent weird failures if you set the readline env vars
                # to something besides a string. Unfortunately, we can't easily
                # raise an exception, since we have to thread in/out of readline,
                # and we can't return a meaningful error code from the bound
                # commands either, because bash doesn't. So, we print an error.
                self.errfmt.Print_(
                    'expected Str for %s, got %s' %
                    (envvar_name, value_str(envvar_val.tag())), loc.Missing)
                return None


class Bind(vm._Builtin):
    """Interactive interface to readline bindings"""

    def __init__(self, readline, errfmt, bindx_cb):
        # type: (Optional[Readline], ui.ErrorFormatter, BindXCallback) -> None
        self.readline = readline
        self.errfmt = errfmt
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

        # Check mutually-exclusive flags and non-flag args
        # Bash allows you to mix args all over, but unfortunately, the execution
        # order is unrelated to the command line order. OSH makes many of the
        # options mutually-exclusive.
        found = False
        for flag in self.exclusive_flags:
            if (flag in attrs.attrs and
                    attrs.attrs[flag].tag() != value_e.Undef):
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

                # Read bindings from a file
                if arg.f is not None:
                    readline.read_init_file(arg.f)

                # Query which keys are bound to a readline fn
                if arg.q is not None:
                    readline.query_bindings(arg.q)

                # Unbind all keys bound to a readline fn
                if arg.u is not None:
                    readline.unbind_rl_function(arg.u)

                # Remove all bindings to a key sequence
                if arg.r is not None:
                    readline.unbind_keyseq(arg.r)

                # Bind custom shell commands to a key sequence
                if arg.x is not None:
                    self._BindShellCmd(arg.x)

                # Print custom shell bindings
                if arg.X:
                    readline.print_shell_cmd_map()

                bindings, arg_locs = arg_r.Rest2()

                # Bind keyseqs to readline fns
                for i, binding in enumerate(bindings):
                    try:
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
        arg_r.Done()

        # TODO:
        # - Exclude lines that don't parse from the history!  bash and zsh don't do
        # that.
        # - Consolidate multiline commands.

        for i in xrange(start_index, num_items + 1):  # 1-based index
            item = readline.get_history_item(i)
            self.f.write('%5d  %s\n' % (i, item))
        return 0


class Fc(vm._Builtin):
    """Show or execute commands from interactive command history."""

    def __init__(
            self,
            mem,  # type: Mem
            readline,  # type: Optional[Readline]
            f,  # type: mylib.Writer
    ):
        # type: (...) -> None
        self.mem = mem
        self.readline = readline
        self.f = f  # this hook is for unit testing only

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        readline = self.readline
        if not readline:
            e_usage("is disabled because Oils wasn't compiled with 'readline'",
                    loc.Missing)

        attrs, arg_r = flag_util.ParseCmdVal('fc', cmd_val)
        arg = arg_types.fc(attrs.attrs)

        # Returns 0 items in non-interactive mode?
        num_items = readline.get_current_history_length()

        first_arg, first_arg_loc = arg_r.Peek2()
        if first_arg is None:
            # Default page size in Bash
            if num_items > 16:
                first_index = -16
            else:
                first_index = 1
        else:
            try:
                # TODO: Support string arg
                first_index = int(first_arg)
            except ValueError:
                e_usage('got invalid argument %r' % first_arg, first_arg_loc)
        if first_index < 0:
            first_index += num_items
        arg_r.Next()

        last_arg, last_arg_loc = arg_r.Peek2()
        if last_arg is None:
            last_index = num_items - 1
        else:
            try:
                # TODO: Support string arg
                last_index = int(last_arg)
            except ValueError:
                e_usage('got invalid argument %r' % last_arg, last_arg_loc)
        if last_index < 0:
            last_index += num_items
        arg_r.Next()

        if self.mem.exec_opts.strict_arg_parse():
            arg_r.Done()

        if arg.l:
            is_reversed = first_index > last_index

            if arg.r and not is_reversed:
                is_reversed = True

                # mycpp requires this swap idiom
                tmp = first_index
                first_index = last_index
                last_index = tmp

            if is_reversed:
                limit = last_index - 1
                step = -1
            else:
                limit = last_index + 1
                step = 1

            i = first_index
            while i != limit:
                item = readline.get_history_item(i)
                if arg.n:
                    self.f.write('\t %s\n' % (item))
                else:
                    self.f.write('%d\t %s\n' % (i, item))
                i += step

            return 0

        # TODO: -e
        if arg.e is not None:
            pass

        # We currently require -l
        e_usage("command editing isn't yet implemented", loc.Missing)
