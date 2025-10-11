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

    def GetTrap(self, sig_num):
        # type: (int) -> command_t
        return self.traps.get(sig_num, None)

    def _AddUserHook(self, hook_name, handler):
        # type: (str, command_t) -> None
        self.hooks[hook_name] = handler

    def _RemoveUserHook(self, hook_name):
        # type: (str) -> None
        mylib.dict_erase(self.hooks, hook_name)

    def _AddUserTrap(self, sig_num, handler):
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

    def _RemoveUserTrap(self, sig_num):
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

    def AddItem(self, parsed_id, handler):
        # type: (str, command_t) -> None
        """Add trap or hook, parsed to EXIT or INT (not 0 or SIGINT)"""
        if parsed_id in _HOOK_NAMES:
            self._AddUserHook(parsed_id, handler)
        else:
            sig_num = signal_def.GetNumber(parsed_id)
            # Should have already been validated
            assert sig_num is not signal_def.NO_SIGNAL

            self._AddUserTrap(sig_num, handler)

    def RemoveItem(self, parsed_id):
        # type: (str) -> None
        """Remove trap or hook, parsed to EXIT or INT (not 0 or SIGINT)"""
        if parsed_id in _HOOK_NAMES:
            self._RemoveUserHook(parsed_id)
        else:
            sig_num = signal_def.GetNumber(parsed_id)
            # Should have already been validated
            assert sig_num is not signal_def.NO_SIGNAL

            self._RemoveUserTrap(sig_num)

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
    sig_spec = sig_spec.upper()
    if sig_spec.strip() in ('1', '2', '3', '6', '9', '13', '14', '15'):
        return int(sig_spec)

    # INT is an alias for SIGINT
    if sig_spec.startswith('SIG'):
        sig_spec = sig_spec[3:]
    return signal_def.GetNumber(sig_spec)


_HOOK_NAMES = ['EXIT', 'ERR', 'RETURN', 'DEBUG']


def _ParseSignalOrHook(user_str, blame_loc):
    # type: (str, loc_t) -> str
    """Convert user string to a parsed/normalized string.

    These can be passed to AddItem() and RemoveItem()

    See unit tests in builtin/trap_osh_test.py
        '0'      -> 'EXIT'
        'EXIT'   -> 'EXIT'
        'eXIT'   -> 'EXIT'

        '2'      -> 'INT'
        'iNT'    -> 'INT'
        'sIGINT' -> 'INT'

        'zz'     -> error
        '-150'   -> error
        '10000'  -> error
    """
    if user_str.isdigit():
        try:
            sig_num = int(user_str)
        except ValueError:
            raise error.Usage("got overflowing integer: %s" % user_str,
                              blame_loc)

        if sig_num == 0:  # Special case
            return 'EXIT'

        name = signal_def.GetName(sig_num)
        if name is None:
            return None
        return name[3:]  # Remove SIG

    user_str = user_str.upper()  # Ignore case

    if user_str in _HOOK_NAMES:
        return user_str

    if user_str.startswith('SIG'):
        user_str = user_str[3:]

    n = signal_def.GetNumber(user_str)
    if n == signal_def.NO_SIGNAL:
        return None

    return user_str


def ParseSignalOrHook(user_str, blame_loc):
    # type: (str, loc_t) -> str
    """Convenience wrapper"""
    parsed_id = _ParseSignalOrHook(user_str, blame_loc)
    if parsed_id is None:
        raise error.Usage('expected signal or hook, got %r' % user_str,
                          blame_loc)
    return parsed_id


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

        # TODO: Print ANY command_t variant
        handler_string = '<unknown>'  # type: str

        if body.tag() == command_e.Simple:
            simple_cmd = cast(command.Simple, body)
            if simple_cmd.blame_tok:
                handler_string = simple_cmd.blame_tok.line.content
        return handler_string

    def _PrintTrapEntry(self, handler, name):
        # type: (command_t, str) -> None
        code = self._GetCommandSourceCode(handler)
        print("trap -- %s %s" % (j8_lite.ShellEncode(code), name))

    def _GetSignalInfo(self, arg_r):
        # type: (args.Reader) -> Tuple[str, str, int, CompoundWord]
        sig_spec, sig_loc = arg_r.ReadRequired2(
            'requires a signal or hook name')

        # sig_key is NORMALIZED sig_spec: a signal number string or string hook
        # name.
        sig_key = None  # type: Optional[str]
        sig_num = signal_def.NO_SIGNAL

        sig_spec = sig_spec.upper()
        if sig_spec in _HOOK_NAMES:
            sig_key = sig_spec
        elif sig_spec == '0':  # Special case
            sig_key = 'EXIT'
        else:
            sig_num = _GetSignalNumber(sig_spec)
            if sig_num != signal_def.NO_SIGNAL:
                sig_key = str(sig_num)

        return sig_spec, sig_key, sig_num, sig_loc

    def _RemoveHandler(self, sig_key, sig_num):
        # type: (str, int) -> None
        if sig_key in _HOOK_NAMES:
            self.trap_state._RemoveUserHook(sig_key)
        elif sig_num != signal_def.NO_SIGNAL:
            self.trap_state._RemoveUserTrap(sig_num)
        else:
            raise AssertionError('Signal or trap')

    def _PrintNames(self):
        # type: () -> None
        for hook_name in _HOOK_NAMES:
            # EXIT is 0, but we hide that
            print('   %s' % hook_name)

        # Iterate over signals and print them
        n = signal_def.MaxSigNumber() + 1
        for sig_num in xrange(n):

            sig_name = signal_def.GetName(sig_num)
            if sig_name is None:
                continue
            print('%2d %s' % (sig_num, sig_name))

    def _PrintState(self):
        # type: () -> None
        for name, handler in iteritems(self.trap_state.hooks):
            self._PrintTrapEntry(handler, name)

        # Print in order of signal number
        n = signal_def.MaxSigNumber() + 1
        for sig_num in xrange(n):
            handler = self.trap_state.GetTrap(sig_num)
            if handler is None:
                continue

            sig_name = signal_def.GetName(sig_num)
            assert sig_name is not None

            self._PrintTrapEntry(handler, sig_name)

    def Run(self, cmd_val):
        # type: (cmd_value.Argv) -> int
        attrs, arg_r = flag_util.ParseCmdVal('trap', cmd_val)
        arg = arg_types.trap(attrs.attrs)

        if arg.p:  # trap -p prints handlers
            self._PrintState()
            return 0

        if arg.l:  # List valid signals and hooks
            self._PrintNames()
            return 0

        # 'trap' with no arguments is equivalent to 'trap -p'
        if arg_r.AtEnd():
            self._PrintState()
            return 0

        # TODO:
        # - Parse everything at once - create a boundary
        #   - Consolidate _GetSignalInfo and _GetSignalNumber
        #   - Normalize hooks and traps into a single representation

        first_arg, first_loc = arg_r.ReadRequired2('requires a code string')
        # Per POSIX, if the first argument to trap is '-' or an
        # unsigned integer, then reset every condition
        # https://pubs.opengroup.org/onlinepubs/9699919799.2018edition/utilities/V3_chap02.html#tag_18_28
        # e.g. 'trap 0 2' or 'trap 0 SIGINT'
        looks_like_unsigned = first_arg.isdigit()
        if first_arg == '-' or looks_like_unsigned:
            # If the first argument is a uint, we need to reset this signal as well
            if looks_like_unsigned:
                parsed_id = ParseSignalOrHook(first_arg, first_loc)
                self.trap_state.RemoveItem(parsed_id)

            # Remove all handlers
            while not arg_r.AtEnd():
                arg_str, arg_loc = arg_r.Peek2()
                parsed_id = ParseSignalOrHook(arg_str, arg_loc)
                self.trap_state.RemoveItem(parsed_id)
                arg_r.Next()
            return 0

        # We read the first arg - "trap SIGNAL" should reset the signal
        if arg_r.AtEnd():
            sig_num = _GetSignalNumber(first_arg)
            if sig_num == signal_def.NO_SIGNAL and first_arg not in _HOOK_NAMES:
                self.errfmt.Print_("Invalid signal or hook %r" % first_arg,
                                   blame_loc=first_loc)
                return 1  # 2 would be usage error, but this matches other shells

            self._RemoveHandler(first_arg, sig_num)
            return 0

        code_str = first_arg
        # Try parsing the code first.
        node = self._ParseTrapCode(code_str)
        if node is None:
            return 1  # _ParseTrapCode() prints an error for us.

        # This command has the form of "trap COMMAND (SIGNAL)*", so read all
        # SIGNALs and add this code as the handler to all of them
        while not arg_r.AtEnd():
            sig_spec, sig_key, sig_num, sig_loc = self._GetSignalInfo(arg_r)
            if sig_key is None:
                self.errfmt.Print_("Invalid signal or hook %r" % sig_spec,
                                   blame_loc=sig_loc)
                return 1  # 2 would be usage error, but this matches other shells

            # Register a hook.
            if sig_key in _HOOK_NAMES:
                if sig_key == 'RETURN':
                    print_stderr("osh warning: The %r hook isn't implemented" %
                                 sig_spec)
                self.trap_state._AddUserHook(sig_key, node)

            # Register a signal.
            if sig_num != signal_def.NO_SIGNAL:
                # For signal handlers, the traps dictionary is used only for debugging.
                if sig_num in (SIGKILL, SIGSTOP):
                    self.errfmt.Print_("Signal %r can't be handled" % sig_spec,
                                       blame_loc=sig_loc)
                    # Other shells return 0, but this seems like an obvious error
                    return 1
                self.trap_state._AddUserTrap(sig_num, node)

        return 0
