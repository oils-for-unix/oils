#!/usr/bin/env python2
"""Builtin_trap.py."""
from __future__ import print_function

from signal import SIG_DFL, SIGINT, SIGKILL, SIGSTOP, SIGWINCH

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.syntax_asdl import loc, source
from core import alloc
from core import dev
from core import error
from core import main_loop
from mycpp.mylib import log
from core import pyos
from core import vm
from frontend import flag_util
from frontend import signal_def
from frontend import reader
from mycpp import mylib
from mycpp.mylib import iteritems, print_stderr

from typing import Dict, List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from _devbuild.gen.syntax_asdl import command_t
    from display import ui
    from frontend.parse_lib import ParseContext

_ = log


class TrapState(object):
    """Traps are shell callbacks that the user wants to run on certain events.

    There are 2 catogires:
    1. Signals like SIGUSR1
    2. Hooks like EXIT

    Signal handlers execute in the main loop, and within blocking syscalls.

    EXIT, DEBUG, ERR, RETURN execute in specific places in the interpreter.
    """

    def __init__(self, signal_safe):
        # type: (pyos.SignalSafe) -> None
        self.signal_safe = signal_safe
        self.hooks = {}  # type: Dict[str, command_t]
        self.traps = {}  # type: Dict[int, command_t]

    def ClearForSubProgram(self, inherit_errtrace):
        # type: (bool) -> None
        """SubProgramThunk uses this because traps aren't inherited."""

        # bash clears hooks like DEBUG in subshells.
        # The ERR can be preserved if set -o errtrace
        hook_err = self.hooks.get('ERR')
        self.hooks.clear()
        if hook_err is not None and inherit_errtrace:
            self.hooks['ERR'] = hook_err

        self.traps.clear()

    def GetHook(self, hook_name):
        # type: (str) -> command_t
        """ e.g. EXIT hook. """
        return self.hooks.get(hook_name, None)

    def AddUserHook(self, hook_name, handler):
        # type: (str, command_t) -> None
        self.hooks[hook_name] = handler

    def RemoveUserHook(self, hook_name):
        # type: (str) -> None
        mylib.dict_erase(self.hooks, hook_name)

    def AddUserTrap(self, sig_num, handler):
        # type: (int, command_t) -> None
        """ e.g. SIGUSR1 """
        self.traps[sig_num] = handler

        if sig_num == SIGINT:
            # Don't disturb the runtime signal handlers:
            # 1. from CPython
            # 2. pyos::InitSignalSafe() calls RegisterSignalInterest(SIGINT)
            self.signal_safe.SetSigIntTrapped(True)
        elif sig_num == SIGWINCH:
            self.signal_safe.SetSigWinchCode(SIGWINCH)
        else:
            pyos.RegisterSignalInterest(sig_num)

    def RemoveUserTrap(self, sig_num):
        # type: (int) -> None

        mylib.dict_erase(self.traps, sig_num)

        if sig_num == SIGINT:
            self.signal_safe.SetSigIntTrapped(False)
        elif sig_num == SIGWINCH:
            self.signal_safe.SetSigWinchCode(pyos.UNTRAPPED_SIGWINCH)
        else:
            # TODO: In process.InitInteractiveShell(), 4 signals are set to
            # SIG_IGN, not SIG_DFL:
            #
            # SIGQUIT SIGTSTP SIGTTOU SIGTTIN
            #
            # Should we restore them?  It's rare that you type 'trap' in
            # interactive shells, but it might be more correct.  See what other
            # shells do.
            pyos.sigaction(sig_num, SIG_DFL)

    def GetPendingTraps(self):
        # type: () -> Optional[List[command_t]]
        """Transfer ownership of queue of pending trap handlers to caller."""
        signals = self.signal_safe.TakePendingSignals()
        if 0:
            log('*** GetPendingTraps')
            for si in signals:
                log('SIGNAL %d', si)
            #import traceback
            #traceback.print_stack()

        # Optimization for the common case: do not allocate a list.  This function
        # is called in the interpreter loop.
        if len(signals) == 0:
            self.signal_safe.ReuseEmptyList(signals)
            return None

        run_list = []  # type: List[command_t]
        for sig_num in signals:
            node = self.traps.get(sig_num, None)
            if node is not None:
                run_list.append(node)

        # Optimization to avoid allocation in the main loop.
        del signals[:]
        self.signal_safe.ReuseEmptyList(signals)

        return run_list

    def ThisProcessHasTraps(self):
        # type: () -> bool
        """
        noforklast optimizations are not enabled when the process has code to
        run after fork!
        """
        if 0:
            log('traps %d', len(self.traps))
            log('hooks %d', len(self.hooks))
        return len(self.traps) != 0 or len(self.hooks) != 0


def _GetSignalNumber(sig_spec):
    # type: (str) -> int

    # POSIX lists the numbers that are required.
    # http://pubs.opengroup.org/onlinepubs/9699919799/
    #
    # Added 13 for SIGPIPE because autoconf's 'configure' uses it!
    if sig_spec.strip() in ('1', '2', '3', '6', '9', '13', '14', '15'):
        return int(sig_spec)

    # INT is an alias for SIGINT
    if sig_spec.startswith('SIG'):
        sig_spec = sig_spec[3:]
    return signal_def.GetNumber(sig_spec)


_HOOK_NAMES = ['EXIT', 'ERR', 'RETURN', 'DEBUG']

# bash's default -p looks like this:
# trap -- '' SIGTSTP
# trap -- '' SIGTTIN
# trap -- '' SIGTTOU
#
# CPython registers different default handlers.  The C++ rewrite should make
# OVM match sh/bash more closely.

# Example of trap:
# trap -- 'echo "hi  there" | wc ' SIGINT
#
# Then hit Ctrl-C.


class Trap(vm._Builtin):

    def __init__(self, trap_state, parse_ctx, tracer, errfmt):
        # type: (TrapState, ParseContext, dev.Tracer, ui.ErrorFormatter) -> None
        self.trap_state = trap_state
        self.parse_ctx = parse_ctx
        self.arena = parse_ctx.arena
        self.tracer = tracer
        self.errfmt = errfmt

    def _ParseTrapCode(self, code_str):
        # type: (str) -> command_t
        """
    Returns:
      A node, or None if the code is invalid.
    """
        line_reader = reader.StringLineReader(code_str, self.arena)
        c_parser = self.parse_ctx.MakeOshParser(line_reader)

        # TODO: the SPID should be passed through argv.
        src = source.ArgvWord('trap', loc.Missing)
        with alloc.ctx_SourceCode(self.arena, src):
            try:
                node = main_loop.ParseWholeFile(c_parser)
            except error.Parse as e:
                self.errfmt.PrettyPrintError(e)
                return None

        return node

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('trap', cmd_val)
        arg = arg_types.trap(attrs.attrs)

        if arg.p:  # Print registered handlers
            # The unit tests rely on this being one line.
            # bash prints a line that can be re-parsed.
            for name, _ in iteritems(self.trap_state.hooks):
                print('%s TrapState' % (name, ))

            for sig_num, _ in iteritems(self.trap_state.traps):
                print('%d TrapState' % (sig_num, ))

            return 0

        if arg.l:  # List valid signals and hooks
            for hook_name in _HOOK_NAMES:
                print('   %s' % hook_name)

            signal_def.PrintSignals()

            return 0

        code_str = arg_r.ReadRequired('requires a code string')
        sig_spec, sig_loc = arg_r.ReadRequired2(
            'requires a signal or hook name')

        # sig_key is NORMALIZED sig_spec: a signal number string or string hook
        # name.
        sig_key = None  # type: Optional[str]
        sig_num = signal_def.NO_SIGNAL

        if sig_spec in _HOOK_NAMES:
            sig_key = sig_spec
        elif sig_spec == '0':  # Special case
            sig_key = 'EXIT'
        else:
            sig_num = _GetSignalNumber(sig_spec)
            if sig_num != signal_def.NO_SIGNAL:
                sig_key = str(sig_num)

        if sig_key is None:
            self.errfmt.Print_("Invalid signal or hook %r" % sig_spec,
                               blame_loc=cmd_val.arg_locs[2])
            return 1

        # NOTE: sig_spec isn't validated when removing handlers.
        if code_str == '-':
            if sig_key in _HOOK_NAMES:
                self.trap_state.RemoveUserHook(sig_key)
                return 0

            if sig_num != signal_def.NO_SIGNAL:
                self.trap_state.RemoveUserTrap(sig_num)
                return 0

            raise AssertionError('Signal or trap')

        # Try parsing the code first.

        # TODO: If simple_trap is on (for oil:upgrade), then it must be a function
        # name?  And then you wrap it in 'try'?

        node = self._ParseTrapCode(code_str)
        if node is None:
            return 1  # ParseTrapCode() prints an error for us.

        # Register a hook.
        if sig_key in _HOOK_NAMES:
            if sig_key == 'RETURN':
                print_stderr("osh warning: The %r hook isn't implemented" %
                             sig_spec)
            self.trap_state.AddUserHook(sig_key, node)
            return 0

        # Register a signal.
        if sig_num != signal_def.NO_SIGNAL:
            # For signal handlers, the traps dictionary is used only for debugging.
            if sig_num in (SIGKILL, SIGSTOP):
                self.errfmt.Print_("Signal %r can't be handled" % sig_spec,
                                   blame_loc=sig_loc)
                # Other shells return 0, but this seems like an obvious error
                return 1
            self.trap_state.AddUserTrap(sig_num, node)
            return 0

        raise AssertionError('Signal or trap')
