#!/usr/bin/env python2
"""
builtin_lib.py - Builtins that are bindings to libraries.
"""
from __future__ import print_function

from osh.builtin_misc import _Builtin

from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import cmd_value__Argv
  from core.ui import ErrorFormatter


class Bind(_Builtin):
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


