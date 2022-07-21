#!/usr/bin/env python2
"""
builtin_process2.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import cmd_value, cmd_value__Argv

from core import vm
from core.pyerror import e_usage
from core.pyutil import stderr_line
from frontend import flag_spec

import posix_ as posix

from typing import TYPE_CHECKING
if TYPE_CHECKING:
  from core.process import ExternalProgram, FdState
  from core.state import Mem, SearchPath
  from core.ui import ErrorFormatter


class Exec(vm._Builtin):

  def __init__(self, mem, ext_prog, fd_state, search_path, errfmt):
    # type: (Mem, ExternalProgram, FdState, SearchPath, ErrorFormatter) -> None
    self.mem = mem
    self.ext_prog = ext_prog
    self.fd_state = fd_state
    self.search_path = search_path
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    _, arg_r = flag_spec.ParseCmdVal('exec', cmd_val)

    # Apply redirects in this shell.  # NOTE: Redirects were processed earlier.
    if arg_r.AtEnd():
      self.fd_state.MakePermanent()
      return 0

    environ = self.mem.GetExported()
    i = arg_r.i
    cmd = cmd_val.argv[i]
    argv0_path = self.search_path.CachedLookup(cmd)
    if argv0_path is None:
      self.errfmt.Print_('exec: %r not found' % cmd,
                         span_id=cmd_val.arg_spids[1])
      raise SystemExit(127)  # exec builtin never returns

    # shift off 'exec'
    c2 = cmd_value.Argv(cmd_val.argv[i:], cmd_val.arg_spids[i:],
                        cmd_val.typed_args)

    self.ext_prog.Exec(argv0_path, c2, environ)  # NEVER RETURNS
    # makes mypy and C++ compiler happy
    raise AssertionError('unreachable')


class Umask(vm._Builtin):

  def __init__(self):
    # type: () -> None
    """Dummy constructor for mycpp."""
    pass

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int

    argv = cmd_val.argv[1:]
    if len(argv) == 0:
      # umask() has a dumb API: you can't get it without modifying it first!
      # NOTE: dash disables interrupts around the two umask() calls, but that
      # shouldn't be a concern for us.  Signal handlers won't call umask().
      mask = posix.umask(0)
      posix.umask(mask)  #
      print('0%03o' % mask)  # octal format
      return 0

    if len(argv) == 1:
      a = argv[0]
      try:
        new_mask = int(a, 8)
      except ValueError:
        # NOTE: This happens if we have '8' or '9' in the input too.
        stderr_line("osh warning: umask with symbolic input isn't implemented")
        return 1
      else:
        posix.umask(new_mask)
        return 0

    e_usage('umask: unexpected arguments')
