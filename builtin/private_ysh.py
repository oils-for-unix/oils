from __future__ import print_function

from errno import EINTR
import time as time_

from core import error
from core.error import e_die_status
from core import pyos
from core import vm
from frontend import flag_util
from mycpp import iolib
from mycpp import mylib
from mycpp.mylib import STDIN_FILENO

import libc
import posix_ as posix

from typing import List, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.runtime_asdl import cmd_value
    from osh import cmd_eval


class Cat(vm._Builtin):
    """Internal implementation detail for $(< file)."""

    def __init__(self):
        # type: () -> None
        vm._Builtin.__init__(self)

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        chunks = []  # type: List[str]
        while True:
            n, err_num = pyos.Read(STDIN_FILENO, 4096, chunks)

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
