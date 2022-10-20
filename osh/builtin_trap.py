#!/usr/bin/env python2
"""
builtin_trap.py
"""
from __future__ import print_function

from signal import SIGKILL, SIGSTOP

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import cmd_value__Argv
from _devbuild.gen.syntax_asdl import source
from asdl import runtime
from core import alloc
from core import dev
from core import error
from core import main_loop
from core import pyos
from core.pyutil import stderr_line
from core import vm
from frontend import flag_spec
from frontend import signal_def
from frontend import reader
from mycpp import mylib
from mycpp.mylib import iteritems

from typing import Optional, Any, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import command_t
  from core.ui import ErrorFormatter
  from frontend.parse_lib import ParseContext


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
  def __init__(self, sig_state, parse_ctx, tracer, errfmt):
    # type: (pyos.SignalState, ParseContext, dev.Tracer, ErrorFormatter) -> None
    self.sig_state = sig_state
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
      if mylib.PYTHON:
        # The unit tests rely on this being one line.
        # bash prints a line that can be re-parsed.
        for name, value in iteritems(self.sig_state.hooks):
          print('%s %s' % (name, value.__class__.__name__))

        for sig_num, value in iteritems(self.sig_state.traps):
          print('%d %s' % (sig_num, value.__class__.__name__))

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
        self.sig_state.RemoveUserHook(sig_key)
        return 0

      if sig_num != signal_def.NO_SIGNAL:
        self.sig_state.RemoveUserTrap(sig_num)
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
        stderr_line("osh warning: The %r hook isn't implemented", sig_spec)
      self.sig_state.AddUserHook(sig_key, node)
      return 0

    # Register a signal.
    if sig_num != signal_def.NO_SIGNAL:
      # For signal handlers, the traps dictionary is used only for debugging.
      if sig_num in (SIGKILL, SIGSTOP):
        self.errfmt.Print_("Signal %r can't be handled" % sig_spec,
                           span_id=sig_spid)
        # Other shells return 0, but this seems like an obvious error
        return 1
      self.sig_state.AddUserTrap(sig_num, node)
      return 0

    raise AssertionError('Signal or trap')
