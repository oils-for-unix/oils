from __future__ import print_function

from errno import EINTR, ENOENT
import time as time_

from _devbuild.gen import arg_types
from core import error
from core.error import e_die_status
from core import pyos
from core import pyutil
from core import vm
from display import ui
from frontend import flag_util
from mycpp import iolib
from mycpp import mylib
from mycpp.mylib import STDIN_FILENO, log

import libc
import posix_ as posix
from posix_ import O_RDONLY

_ = log

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value
    from osh import cmd_eval


class Cat(vm._Builtin):
    """Internal implementation detail for $(< file)."""

    def __init__(self, errfmt):
        # type: (ui.ErrorFormatter) -> None
        vm._Builtin.__init__(self)
        self.errfmt = errfmt
        self.stdout_ = mylib.Stdout()

    def _CatFile(self, fd):
        # type: (int) -> int

        chunks = []  # type: List[str]
        while True:
            n, err_num = pyos.Read(fd, 4096, chunks)

            if n < 0:
                if err_num == EINTR:
                    # Note: When running external cat, shells don't run traps
                    # until after cat is done.  It seems like they could?  In
                    # any case, we don't do it here, which makes it
                    # inconsistent with 'builtin sleep'.  'sleep' was modelled
                    # after 'read -t N'.  Could have shopt for this?  Maybe fix
                    # it in YSH?

                    pass  # retry
                else:
                    # Like the top level IOError handler
                    e_die_status(
                        2, 'oils I/O error: %s' % posix.strerror(err_num))
                    # TODO: Maybe just return 1?

            elif n == 0:  # EOF
                break

            else:
                # Stream it to stdout
                assert len(chunks) == 1
                self.stdout_.write(chunks[0])
                chunks.pop()

        return 0

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        _, arg_r = flag_util.ParseCmdVal('cat', cmd_val)

        argv, locs = arg_r.Rest2()
        #log('argv %r', argv)

        if len(argv) == 0:
            return self._CatFile(STDIN_FILENO)

        status = 0
        for i, path in enumerate(argv):
            if path == '-':
                st = self._CatFile(STDIN_FILENO)
                if st != 0:
                    status = st
                continue

            # 0o666 is affected by umask, all shells use it.
            opened = False
            try:
                my_fd = posix.open(path, O_RDONLY, 0)
                opened = True
            except (IOError, OSError) as e:
                self.errfmt.Print_("Can't open %r: %s" %
                                   (path, pyutil.strerror(e)),
                                   blame_loc=locs[i])
                status = 1

            if opened:
                st = self._CatFile(my_fd)
                posix.close(my_fd)
                if st != 0:
                    status = st

        return status


class Rm(vm._Builtin):

    def __init__(self, errfmt):
        # type: (ui.ErrorFormatter) -> None
        vm._Builtin.__init__(self)
        self.errfmt = errfmt

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('rm', cmd_val)
        arg = arg_types.rm(attrs.attrs)

        argv, locs = arg_r.Rest2()
        #log('argv %r', argv)

        if not arg.f and len(argv) == 0:
            raise error.Usage('expected one or more files',
                              cmd_val.arg_locs[0])

        status = 0
        for i, path in enumerate(argv):
            err_num = pyos.Unlink(path)

            # -f ignores nonexistent files
            if arg.f and err_num == ENOENT:
                continue

            if err_num != 0:
                self.errfmt.Print_("Can't remove %r: %s" %
                                   (path, posix.strerror(err_num)),
                                   blame_loc=locs[i])
                status = 1

        return status


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
