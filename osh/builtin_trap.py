#!/usr/bin/env python2
"""
builtin_trap.py
"""
from __future__ import print_function

from signal import (
    SIG_DFL, SIG_IGN, SIGKILL, SIGSTOP, SIGQUIT, SIGTSTP, SIGTTOU, SIGTTIN,
    SIGWINCH
)

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value__Argv
from _devbuild.gen.syntax_asdl import source
from asdl import runtime
from core import alloc
from core import dev
from core import error
from core import main_loop
from core import pyos
from core import vm
from frontend import flag_spec
from frontend import signal_def
from frontend import reader
from mycpp import mylib
from mycpp.mylib import iteritems, print_stderr

from typing import Dict, List, Optional, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import command_t
  from core.comp_ui import _IDisplay
  from core.ui import ErrorFormatter
  from frontend.parse_lib import ParseContext


class TrapState(object):
  """All changes to global signal and hook state go through this object."""
  def __init__(self):
    # type: () -> None
    self.hooks = {}  # type: Dict[str, command_t]
    self.traps = {}  # type: Dict[int, command_t]
    self.display = None  # type: _IDisplay

  def GetHook(self, hook_name):
    # type: (str) -> command_t
    """Return the handler associated with hook_name"""
    return self.hooks.get(hook_name, None)

  def AddUserHook(self, hook_name, handler):
    # type: (str, command_t) -> None
    """For user-defined handlers registered with the 'trap' builtin."""
    self.hooks[hook_name] = handler

  def RemoveUserHook(self, hook_name):
    # type: (str) -> None
    """For user-defined handlers registered with the 'trap' builtin."""
    mylib.dict_erase(self.hooks, hook_name)

  def AddUserTrap(self, sig_num, handler):
    # type: (int, command_t) -> None
    """For user-defined handlers registered with the 'trap' builtin."""
    self.traps[sig_num] = handler

    if sig_num == SIGWINCH:
      assert self.display is not None
      pyos.SetSigwinchCode(SIGWINCH)
    else:
      pyos.RegisterSignalInterest(sig_num)
    # TODO: SIGINT is similar: set a flag, then optionally call user _TrapHandler

  def RemoveUserTrap(self, sig_num):
    # type: (int) -> None
    """For user-defined handlers registered with the 'trap' builtin."""
    # Restore default
    mylib.dict_erase(self.traps, sig_num)

    if sig_num == SIGWINCH:
      pyos.SetSigwinchCode(pyos.UNTRAPPED_SIGWINCH)
    else:
      pyos.Sigaction(sig_num, SIG_DFL)
    # TODO: SIGINT is similar: set a flag, then optionally call user _TrapHandler

  def InitShell(self):
    # type: () -> None
    """Always called when initializing the shell process."""
    pyos.InitShell()

  def InitInteractiveShell(self, display, my_pid):
    # type: (_IDisplay, int) -> None
    """Called when initializing an interactive shell."""
    # The shell itself should ignore Ctrl-\.
    pyos.Sigaction(SIGQUIT, SIG_IGN)

    # This prevents Ctrl-Z from suspending OSH in interactive mode.
    pyos.Sigaction(SIGTSTP, SIG_IGN)

    # More signals from
    # https://www.gnu.org/software/libc/manual/html_node/Initializing-the-Shell.html
    # (but not SIGCHLD)
    pyos.Sigaction(SIGTTOU, SIG_IGN)
    pyos.Sigaction(SIGTTIN, SIG_IGN)

    # Register a callback to receive terminal width changes.
    # NOTE: In line_input.c, we turned off rl_catch_sigwinch.

    # This is ALWAYS on, which means that it can cause EINTR, and wait() and
    # read() have to handle it
    self.display = display
    pyos.RegisterSignalInterest(SIGWINCH)
    pyos.SetSigwinchCode(pyos.UNTRAPPED_SIGWINCH)

  def GetLastSignal(self):
    # type: () -> int
    """Return the last signal that fired"""
    return pyos.LastSignal()

  def TakeRunList(self):
      # type: () -> List[command_t]
      """Transfer ownership of the current queue of pending trap handlers to the caller."""
      sig_queue = pyos.TakeSignalQueue()

      run_list = []  # type: List[command_t]
      for sig_num in sig_queue:
        node = self.traps.get(sig_num, None)

        if sig_num == SIGWINCH:
          if mylib.PYTHON:
            self.display.OnWindowChange()
          if node is None:
            continue

        assert node is not None
        run_list.append(node)

      return run_list


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
    # type: (TrapState, ParseContext, dev.Tracer, ErrorFormatter) -> None
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
    src = source.ArgvWord('trap', runtime.NO_SPID)
    with alloc.ctx_Location(self.arena, src):
      try:
        node = main_loop.ParseWholeFile(c_parser)
      except error.Parse as e:
        self.errfmt.PrettyPrintError(e)
        return None

    return node

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    attrs, arg_r = flag_spec.ParseCmdVal('trap', cmd_val)
    arg = arg_types.trap(attrs.attrs)

    if arg.p:  # Print registered handlers
      # The unit tests rely on this being one line.
      # bash prints a line that can be re-parsed.
      for name, _ in iteritems(self.trap_state.hooks):
        print('%s TrapState' % (name,))

      for sig_num, _ in iteritems(self.trap_state.traps):
        print('%d TrapState' % (sig_num,))

      return 0

    if arg.l:  # List valid signals and hooks
      for name in _HOOK_NAMES:
        print('   %s' % name)

      signal_def.PrintSignals()

      return 0

    code_str = arg_r.ReadRequired('requires a code string')
    sig_spec, sig_spid = arg_r.ReadRequired2('requires a signal or hook name')

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
                         span_id=cmd_val.arg_spids[2])
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
      if sig_key in ('ERR', 'RETURN', 'DEBUG'):
        print_stderr("osh warning: The %r hook isn't implemented" % sig_spec)
      self.trap_state.AddUserHook(sig_key, node)
      return 0

    # Register a signal.
    if sig_num != signal_def.NO_SIGNAL:
      # For signal handlers, the traps dictionary is used only for debugging.
      if sig_num in (SIGKILL, SIGSTOP):
        self.errfmt.Print_("Signal %r can't be handled" % sig_spec,
                           span_id=sig_spid)
        # Other shells return 0, but this seems like an obvious error
        return 1
      self.trap_state.AddUserTrap(sig_num, node)
      return 0

    raise AssertionError('Signal or trap')
