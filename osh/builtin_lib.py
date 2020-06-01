#!/usr/bin/env python2
"""
builtin_lib.py - Builtins that are bindings to libraries, e.g. GNU readline.
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from core import vm
from core.pyerror import e_usage
from frontend import flag_spec
from mycpp import mylib

from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv
  from core.ui import ErrorFormatter


class Bind(vm._Builtin):
  """For :, true, false."""
  def __init__(self, readline_mod, errfmt):
    # type: (Any, ErrorFormatter) -> None
    self.readline_mod = readline_mod
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    self.errfmt.Print("warning: bind isn't implemented",
                      span_id=cmd_val.arg_spids[0])
    return 1


class History(vm._Builtin):
  """Show interactive command history."""

  def __init__(self, readline_mod, f):
    # type: (Any, mylib.Writer) -> None
    self.readline_mod = readline_mod
    self.f = f  # this hook is for unit testing only

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    # NOTE: This builtin doesn't do anything in non-interactive mode in bash?
    # It silently exits zero.
    # zsh -c 'history' produces an error.
    readline_mod = self.readline_mod
    if not readline_mod:
      e_usage("is disabled because Oil wasn't compiled with 'readline'")

    attrs, arg_r = flag_spec.ParseCmdVal('history', cmd_val)
    arg = arg_types.history(attrs.attrs)

    # Clear all history
    if arg.c:
      readline_mod.clear_history()
      return 0

    # Delete history entry by id number
    if arg.d >= 0:
      cmd_index = arg.d - 1

      try:
        readline_mod.remove_history_item(cmd_index)
      except ValueError:
        e_usage("couldn't find item %d" % arg.d)

      return 0

    # Returns 0 items in non-interactive mode?
    num_items = readline_mod.get_current_history_length()
    #log('len = %d', num_items)

    rest = arg_r.Rest()
    if len(rest) == 0:
      start_index = 1
    elif len(rest) == 1:
      arg0 = rest[0]
      try:
        num_to_show = int(arg0)
      except ValueError:
        e_usage('got invalid argument %r' % arg0)
      start_index = max(1, num_items + 1 - num_to_show)
    else:
      e_usage('got many arguments')

    # TODO:
    # - Exclude lines that don't parse from the history!  bash and zsh don't do
    # that.
    # - Consolidate multiline commands.

    for i in xrange(start_index, num_items+1):  # 1-based index
      item = readline_mod.get_history_item(i)
      self.f.write('%5d  %s\n' % (i, item))
    return 0
