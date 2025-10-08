#!/usr/bin/env python2
from __future__ import print_function

from signal import SIG_DFL, SIGINT, SIGKILL, SIGSTOP, SIGWINCH

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value
from _devbuild.gen.syntax_asdl import loc, loc_t, source, command_e, command, CompoundWord
from core import alloc
from core import dev
from core import error
from core import main_loop
from core import vm
from frontend import args
from frontend import flag_util
from frontend import match
from frontend import reader
from frontend import signal_def
from data_lang import j8_lite
from mycpp import iolib
from mycpp import mylib
from mycpp.mylib import iteritems, print_stderr, log
from mycpp import mops

from typing import Dict, List, Optional, TYPE_CHECKING, cast, Tuple
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
        # type: (iolib.SignalSafe) -> None
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
            # Don't disturb the underlying runtime's SIGINT handllers
            # 1. CPython has one for KeyboardInterrupt
            # 2. mycpp runtime simulates KeyboardInterrupt:
            #    pyos::InitSignalSafe() calls RegisterSignalInterest(SIGINT),
            #    then we PollSigInt() in the osh/cmd_eval.py main loop
            self.signal_safe.SetSigIntTrapped(True)
        elif sig_num == SIGWINCH:
            self.signal_safe.SetSigWinchCode(SIGWINCH)
        else:
            iolib.RegisterSignalInterest(sig_num)

    def RemoveUserTrap(self, sig_num):
        # type: (int) -> None

        mylib.dict_erase(self.traps, sig_num)

        if sig_num == SIGINT:
            self.signal_safe.SetSigIntTrapped(False)
            pass
        elif sig_num == SIGWINCH:
            self.signal_safe.SetSigWinchCode(iolib.UNTRAPPED_SIGWINCH)
        else:
            # TODO: In process.InitInteractiveShell(), 4 signals are set to
            # SIG_IGN, not SIG_DFL:
            #
            # SIGQUIT SIGTSTP SIGTTOU SIGTTIN
            #
            # Should we restore them?  It's rare that you type 'trap' in
            # interactive shells, but it might be more correct.  See what other
            # shells do.
            iolib.sigaction(sig_num, SIG_DFL)

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


def _IsUnsignedInteger(s, blame_loc):
    # type: (str, loc_t) -> bool
    if not match.LooksLikeInteger(s):
        return False

    # Note: could simplify this by making match.LooksLikeUnsigned()

    ok, big_int = mops.FromStr2(s)
    if not ok:
        raise error.Usage('integer too big: %s' % s, blame_loc)

    # not (0 > s) is (s >= 0)
    return not mops.Greater(mops.ZERO, big_int)


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
        src = source.Dynamic('trap arg', loc.Missing)
        with alloc.ctx_SourceCode(self.arena, src):
            try:
                node = main_loop.ParseWholeFile(c_parser)
            except error.Parse as e:
                self.errfmt.PrettyPrintError(e)
                return None

        return node

    def _GetCommandSourceCode(self, body):
        # type: (command_t) -> str
        handler_string = 'TrapState'  # type: str
        if body.tag() == command_e.Simple:
            simple_cmd = cast(command.Simple, body)
            if simple_cmd.blame_tok:
                handler_string = simple_cmd.blame_tok.line.content
        return j8_lite.ShellEncode(handler_string)

    def _GetSignalInfo(self, arg_r):
        # type: (args.Reader) -> Tuple[str, str, int, CompoundWord]
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

        return sig_spec, sig_key, sig_num, sig_loc

    def _ResetSignal(self, sig_key, sig_num):
        # type: (str, int) -> None
        if sig_key in _HOOK_NAMES:
            self.trap_state.RemoveUserHook(sig_key)
        elif sig_num != signal_def.NO_SIGNAL:
            self.trap_state.RemoveUserTrap(sig_num)
        else:
            raise AssertionError('Signal or trap')

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('trap', cmd_val)
        arg = arg_types.trap(attrs.attrs)

        # 'trap' with no arguments is equivalent to 'trap -p'
        if arg.p or arg_r.n == 1:  # Print registered handlers
            for name, handler in iteritems(self.trap_state.hooks):
                print("trap -- %s %s" %
                      (self._GetCommandSourceCode(handler), name))

            for sig_num, handler in iteritems(self.trap_state.traps):
                sig_name = signal_def.GetName(sig_num)
                print("trap -- %s %s" %
                      (self._GetCommandSourceCode(handler), sig_name))

            return 0

        if arg.l:  # List valid signals and hooks
            for hook_name in _HOOK_NAMES:
                print('   %s' % hook_name)

            signal_def.PrintSignals()

            return 0

        code_str, code_loc = arg_r.ReadRequired2('requires a code string')
        # Per POSIX, if the first argument to trap is an unsigned integer
        # then reset every condition
        # https://pubs.opengroup.org/onlinepubs/9699919799.2018edition/utilities/V3_chap02.html#tag_18_28
        if _IsUnsignedInteger(code_str, code_loc):
            code_num = int(code_str)
            # 0 is the number for the EXIT pseudo-signal in bash
            if code_num == 0:
                self.trap_state.RemoveUserHook('EXIT')
            else:
                self.trap_state.RemoveUserTrap(code_num)
            # reset every following signal, if any
            for i in xrange(2, arg_r.n):
                sig_spec, sig_key, sig_num, _ = self._GetSignalInfo(arg_r)
                if sig_key is None:
                    self.errfmt.Print_("Invalid signal or hook %r" % sig_spec,
                                       blame_loc=cmd_val.arg_locs[2])
                    return 1
                self._ResetSignal(sig_key, sig_num)
            return 0

        # "trap SIGNAL" should reset the signal
        if arg_r.n == 2:
            code_num = _GetSignalNumber(code_str)
            if code_num == signal_def.NO_SIGNAL and code_str not in _HOOK_NAMES:
                self.errfmt.Print_("Invalid signal or hook %r" % code_str,
                                   blame_loc=cmd_val.arg_locs[1])
                return 2

            self._ResetSignal(code_str, code_num)
            return 0

        # this command has the form of "trap COMMAND SIGNAL", so read SIGNAL
        sig_spec, sig_key, sig_num, sig_loc = self._GetSignalInfo(arg_r)
        if sig_key is None:
            self.errfmt.Print_("Invalid signal or hook %r" % sig_spec,
                               blame_loc=cmd_val.arg_locs[2])
            return 1

        # NOTE: sig_spec isn't validated when removing handlers.
        if code_str == '-':
            self._ResetSignal(sig_key, sig_num)
            return 0

        # Try parsing the code first.

        # TODO: If simple_trap is on (for ysh:upgrade), then it must be a function
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
