from __future__ import print_function

from errno import EINTR
import time as time_

from _devbuild.gen import arg_types
from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.value_asdl import (value, value_t)
from builtin import read_osh
from core import error
from core.error import e_die_status
from core import optview
from core import pyos
from core import state
from core import vm
from frontend import flag_util
from frontend import match
from frontend import typed_args
from mycpp import iolib
from mycpp import mylib
from mycpp.mylib import log
from osh import word_compile

import libc
import posix_ as posix

from typing import List, Dict, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value
    from display import ui
    from osh import cmd_eval

_ = log


class Echo(vm._Builtin):
    """echo builtin.

    shopt -s simple_echo disables -e and -n.
    """

    def __init__(self, exec_opts):
        # type: (optview.Exec) -> None
        self.exec_opts = exec_opts
        self.f = mylib.Stdout()

        # Reuse this constant instance
        self.simple_flag = None  # type: arg_types.echo

    def _SimpleFlag(self):
        # type: () -> arg_types.echo
        """For arg.e and arg.n without parsing."""
        if self.simple_flag is None:
            attrs = {}  # type: Dict[str, value_t]
            attrs['e'] = value.Bool(False)
            attrs['n'] = value.Bool(False)
            self.simple_flag = arg_types.echo(attrs)
        return self.simple_flag

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        argv = cmd_val.argv[1:]

        if self.exec_opts.simple_echo():
            typed_args.DoesNotAccept(cmd_val.proc_args)  # Disallow echo (42)
            arg = self._SimpleFlag()  # Avoid parsing -e -n
        else:
            attrs, arg_r = flag_util.ParseLikeEcho('echo', cmd_val)
            arg = arg_types.echo(attrs.attrs)
            argv = arg_r.Rest()

        backslash_c = False  # \c terminates input

        if arg.e:
            new_argv = []  # type: List[str]
            for a in argv:
                parts = []  # type: List[str]
                lex = match.EchoLexer(a)
                while not backslash_c:
                    id_, s = lex.Next()
                    if id_ == Id.Eol_Tok:  # Note: This is really a NUL terminator
                        break

                    p = word_compile.EvalCStringToken(id_, s)

                    # Unusual behavior: '\c' prints what is there and aborts
                    # processing!
                    if p is None:
                        backslash_c = True
                        break

                    parts.append(p)

                new_argv.append(''.join(parts))
                if backslash_c:  # no more args either
                    break

            # Replace it
            argv = new_argv

        buf = mylib.BufWriter()

        #log('echo argv %s', argv)
        for i, a in enumerate(argv):
            if i != 0:
                buf.write(' ')  # arg separator
            buf.write(a)

        if not arg.n and not backslash_c:
            buf.write('\n')

        self.f.write(buf.getvalue())
        return 0


class MapFile(vm._Builtin):
    """Mapfile / readarray."""

    def __init__(self, mem, errfmt, cmd_ev):
        # type: (state.Mem, ui.ErrorFormatter, cmd_eval.CommandEvaluator) -> None
        self.mem = mem
        self.errfmt = errfmt
        self.cmd_ev = cmd_ev

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('mapfile', cmd_val)
        arg = arg_types.mapfile(attrs.attrs)

        var_name, _ = arg_r.Peek2()
        if var_name is None:
            var_name = 'MAPFILE'

        lines = []  # type: List[str]
        while True:
            # bash uses this slow algorithm; YSH could provide read --all-lines
            try:
                line, eof = read_osh.ReadLineSlowly(self.cmd_ev,
                                                    with_eol=not arg.t)
            except pyos.ReadError as e:
                self.errfmt.PrintMessage("mapfile: read() error: %s" %
                                         posix.strerror(e.err_num))
                return 1
            if eof:
                break
            lines.append(line)

        state.BuiltinSetArray(self.mem, var_name, lines)
        return 0


class Cat(vm._Builtin):
    """Internal implementation detail for $(< file)."""

    def __init__(self):
        # type: () -> None
        vm._Builtin.__init__(self)

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        chunks = []  # type: List[str]
        while True:
            n, err_num = pyos.Read(0, 4096, chunks)

            if n < 0:
                if err_num == EINTR:
                    pass  # retry
                else:
                    # Like the top level IOError handler
                    e_die_status(2,
                                 'osh I/O error: %s' % posix.strerror(err_num))
                    # TODO: Maybe just return 1?

            elif n == 0:  # EOF
                break

            else:
                # Stream it to stdout
                assert len(chunks) == 1
                mylib.Stdout().write(chunks[0])
                chunks.pop()

        return 0


class Sleep(vm._Builtin):
    """Similar to external sleep, but runs pending traps.

    It's related to bash 'read -t 5', which also runs pending traps.

    There is a LARGE test matrix, see test/manual.sh

    Untrapped SIGWINCH, SIGUSR1, ... - Ignore, but run PENDING TRAPS
    Trapped   SIGWINCH, SIGUSR1, ... - Run trap handler

    Untrapped SIGINT / Ctrl-C
      Interactive: back to prompt
      Non-interactive: abort shell interpreter
    Trapped SIGINT - Run trap handler
    """

    def __init__(self, cmd_ev, signal_safe):
        # type: (cmd_eval.CommandEvaluator, iolib.SignalSafe) -> None
        vm._Builtin.__init__(self)
        self.cmd_ev = cmd_ev
        self.signal_safe = signal_safe

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('sleep', cmd_val)

        # Only supports integral seconds
        # https://pubs.opengroup.org/onlinepubs/9699919799/utilities/sleep.html

        duration, duration_loc = arg_r.Peek2()
        if duration is None:
            raise error.Usage('expected a number of seconds',
                              cmd_val.arg_locs[0])
        arg_r.Next()
        arg_r.Done()

        msg = 'got invalid number of seconds %r' % duration
        try:
            total_seconds = float(duration)
        except ValueError:
            raise error.Usage(msg, duration_loc)

        if total_seconds < 0:
            raise error.Usage(msg, duration_loc)

        # time_.time() is inaccurate!
        deadline = time_.time() + total_seconds
        secs = total_seconds  # initial value is the total
        while True:
            err_num = libc.sleep_until_error(secs)
            if err_num == 0:
                # log('finished sleeping')
                break
            elif err_num == EINTR:
                # log('EINTR')

                # e.g. Run traps on SIGWINCH, and keep going
                self.cmd_ev.RunPendingTraps()

                if self.signal_safe.PollUntrappedSigInt():
                    # Ctrl-C aborts in non-interactive mode
                    # log('KeyboardInterrupt')
                    raise KeyboardInterrupt()
            else:
                # Abort sleep on other errors (should be rare)
                break

            # how much time is left?
            secs = deadline - time_.time()
            # log('continue sleeping %s', str(secs))
            if secs <= 0:  # only pass positive values to sleep_until_error()
                break

        return 0
