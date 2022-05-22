#!/usr/bin/env python2
"""
funcs.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value
from _devbuild.gen.syntax_asdl import source
from asdl import runtime
from core import alloc
from core import error
from core import main_loop
from core import state
from core import ui
from frontend import reader

import posix_ as posix

from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import value_t
  from core import process
  from frontend import parse_lib


class ConfigParser(object):
  """ For parse_config()

  """
  def __init__(self, fd_state, parse_ctx, errfmt):
    # type: (process.FdState, parse_lib.ParseContext, ui.ErrorFormatter) -> None
    self.fd_state = fd_state
    self.parse_ctx = parse_ctx
    self.errfmt = errfmt

  def ParseFile(self, path):
    # type: (str) -> value_t

    call_spid = runtime.NO_SPID  # TODO: location info

    # TODO: need to close the file!
    try:
      f = self.fd_state.Open(path)
    except (IOError, OSError) as e:
      msg = posix.strerror(e.errno)
      raise error.Expr("Couldn't open %r: %s" % (path, msg), span_id=call_spid)

    arena = self.parse_ctx.arena
    line_reader = reader.FileLineReader(f, arena)

    parse_opts = state.MakeOilOpts()
    # Note: runtime needs these options and totally different memory

    # TODO: CommandParser needs parse_opts
    c_parser = self.parse_ctx.MakeConfigParser(line_reader)

    # TODO: Should there be a separate config file source?
    src = source.SourcedFile(path, call_spid)
    try:
      with alloc.ctx_Location(arena, src):
        node = main_loop.ParseWholeFile(c_parser)
    except error.Parse as e:
      self.errfmt.PrettyPrintError(e)
      return None

    # Wrap in expr.Block?
    return value.Block(node)
