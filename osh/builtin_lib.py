#!/usr/bin/env python2
"""
builtin_lib.py - Builtins that are bindings to libraries, e.g. GNU readline.
"""
from __future__ import print_function

from _devbuild.gen import arg_types
from _devbuild.gen.runtime_asdl import value_e, value__Str
from _devbuild.gen.syntax_asdl import loc
from core import error
from core import state
from core import vm
from core.pyerror import e_usage
from frontend import flag_spec
from mycpp import mylib
from pylib import path_stat

from typing import Optional, cast, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv
  from frontend.py_readline import Readline
  from core.ui import ErrorFormatter


class Bind(vm._Builtin):
  """For :, true, false."""
  def __init__(self, readline, errfmt):
    # type: (Optional[Readline], ErrorFormatter) -> None
    self.readline = readline
    self.errfmt = errfmt

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    self.errfmt.Print_("warning: bind isn't implemented",
                       blame_loc=cmd_val.arg_locs[0])
    return 1


class History(vm._Builtin):
  """Show interactive command history."""

  def __init__(self, readline, mem, errfmt, f):
    # type: (Optional[Readline], state.Mem, ErrorFormatter, mylib.Writer) -> None
    self.readline = readline
    self.mem = mem
    self.errfmt = errfmt
    self.f = f  # this hook is for unit testing only

  def GetHistoryFilename(self):
    # type: () -> str
    # TODO: In non-strict mode we should try to cast the HISTFILE value to a
    # string following bash's rules

    UP_val = self.mem.GetValue('HISTFILE')
    if UP_val.tag_() == value_e.Str:
      val = cast(value__Str, UP_val)
      return val.s
    else:
      # TODO: support bash-like behaviour here where we try to convert $HISTFILE
      # to a string in anyway possible

      # TODO: can we recover line information here?
      #       might be useful to show where HISTFILE was set
      raise error.Strict("$HISTFILE should only ever be a string", loc.Missing())

  def Run(self, cmd_val):
    # type: (cmd_value__Argv) -> int
    # NOTE: This builtin doesn't do anything in non-interactive mode in bash?
    # It silently exits zero.
    # zsh -c 'history' produces an error.
    readline = self.readline
    if not readline:
      e_usage("is disabled because Oil wasn't compiled with 'readline'", loc.Missing())

    attrs, arg_r = flag_spec.ParseCmdVal('history', cmd_val)
    arg = arg_types.history(attrs.attrs)

    # Clear all history
    if arg.c:
      readline.clear_history()
      return 0

    if arg.a:
      readline.write_history_file(self.GetHistoryFilename())
      return 0

    if arg.r:
      history_filename = self.GetHistoryFilename()
      if not path_stat.exists(history_filename):
        self.errfmt.Print_("The file '%s' ($HISTFILE) does not exist" % history_filename, loc.Missing())
        return 1

      readline.read_history_file(history_filename)
      return 0

    # Delete history entry by id number
    if arg.d >= 0:
      cmd_index = arg.d - 1

      try:
        readline.remove_history_item(cmd_index)
      except ValueError:
        e_usage("couldn't find item %d" % arg.d, loc.Missing())

      return 0

    # Returns 0 items in non-interactive mode?
    num_items = readline.get_current_history_length()
    #log('len = %d', num_items)

    rest = arg_r.Rest()
    if len(rest) == 0:
      start_index = 1
    elif len(rest) == 1:
      arg0 = rest[0]
      try:
        num_to_show = int(arg0)
      except ValueError:
        e_usage('got invalid argument %r' % arg0, loc.Missing())
      start_index = max(1, num_items + 1 - num_to_show)
    else:
      e_usage('got many arguments', loc.Missing())

    # TODO:
    # - Exclude lines that don't parse from the history!  bash and zsh don't do
    # that.
    # - Consolidate multiline commands.

    for i in xrange(start_index, num_items+1):  # 1-based index
      item = readline.get_history_item(i)
      self.f.write('%5d  %s\n' % (i, item))
    return 0
