#!/usr/bin/env python2
"""
funcs.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, value_e, value__Block
from _devbuild.gen.syntax_asdl import source
from asdl import runtime
from core import alloc
from core import error
from core import main_loop
from core import state
from core import ui
from frontend import reader

from mycpp import mylib

import posix_ as posix

from typing import TYPE_CHECKING, cast, Any, Dict

if TYPE_CHECKING:
  from _devbuild.gen.runtime_asdl import value_t
  from _devbuild.gen.syntax_asdl import command_t
  from core import process
  from frontend import parse_lib
  from osh import cmd_eval


class ParseConfig(object):
  """ parse_config() """

  def __init__(self, fd_state, parse_ctx, errfmt):
    # type: (process.FdState, parse_lib.ParseContext, ui.ErrorFormatter) -> None
    self.fd_state = fd_state
    self.parse_ctx = parse_ctx
    self.errfmt = errfmt

  def Call(self, path):
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


class EvalToDict(object):
  """ eval_to_dict() """
  def __init__(self, cmd_ev):
    # type: (cmd_eval.CommandEvaluator) -> None
    self.cmd_ev = cmd_ev

  if mylib.PYTHON:
    # Hard to translate the Dict[str, Any]

    def Call(self, block):
      # type: (value_t) -> Dict[str, Any]

      call_spid = runtime.NO_SPID
      if block.tag_() != value_e.Block:
        raise error.Expr('Expected a block, got %s' % block, span_id=call_spid)

      UP_block = block
      block = cast(value__Block, UP_block)
      top_namespace = self.cmd_ev.EvalBlock(block.body)

      # TODO: get rid of cells, value.Str() etc.
      # _
      return top_namespace

      # Note: we should discourage the unvalidated top namesapce for files?  It
      # needs more validation.
