#!/usr/bin/env python2
"""func_hay.py."""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, value_e
from _devbuild.gen.syntax_asdl import source, loc
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
    from core import process
    from frontend import parse_lib
    from osh import cmd_eval


class ParseHay(object):
    """parseHay()"""

    def __init__(self, fd_state, parse_ctx, errfmt):
        # type: (process.FdState, parse_lib.ParseContext, ui.ErrorFormatter) -> None
        self.fd_state = fd_state
        self.parse_ctx = parse_ctx
        self.errfmt = errfmt

    def Call(self, path):
        # type: (str) -> value_t

        call_loc = loc.Missing  # TODO: location info

        # TODO: need to close the file!
        try:
            f = self.fd_state.Open(path)
        except (IOError, OSError) as e:
            msg = posix.strerror(e.errno)
            raise error.Expr("Couldn't open %r: %s" % (path, msg), call_loc)

        arena = self.parse_ctx.arena
        line_reader = reader.FileLineReader(f, arena)

        parse_opts = state.MakeOilOpts()
        # Note: runtime needs these options and totally different memory

        # TODO: CommandParser needs parse_opts
        c_parser = self.parse_ctx.MakeConfigParser(line_reader)

        # TODO: Should there be a separate config file source?
        src = source.SourcedFile(path, call_loc)
        try:
            with alloc.ctx_Location(arena, src):
                node = main_loop.ParseWholeFile(c_parser)
        except error.Parse as e:
            self.errfmt.PrettyPrintError(e)
            return None

        # Wrap in expr.Block?
        return value.Block(node)


class EvalHay(object):
    """evalHay()"""

    def __init__(self, hay_state, mutable_opts, mem, cmd_ev):
        # type: (state.Hay, state.MutableOpts, state.Mem, cmd_eval.CommandEvaluator) -> None
        self.hay_state = hay_state
        self.mutable_opts = mutable_opts
        self.mem = mem
        self.cmd_ev = cmd_ev

    def Call(self, val):
        # type: (value_t) -> Dict[str, value_t]

        call_loc = loc.Missing
        if val.tag() != value_e.Block:
            raise error.Expr('Expected a block, got %s' % val, call_loc)

        block = cast(value.Block, val)
        with state.ctx_HayEval(self.hay_state, self.mutable_opts,
                               self.mem):
            unused = self.cmd_ev.EvalBlock(block.body)

        return self.hay_state.Result()

        # Note: we should discourage the unvalidated top namesapce for files?  It
        # needs more validation.


class BlockAsStr(object):
    """block_as_str()"""

    def __init__(self, arena):
        # type: (alloc.Arena) -> None
        self.arena = arena

    def Call(self, block):
        # type: (value_t) -> value_t
        return block


class HayFunc(object):
    """_hay() register"""

    def __init__(self, hay_state):
        # type: (state.Hay) -> None
        self.hay_state = hay_state

    def Call(self):
        # type: () -> Dict[str, value_t]
        return self.hay_state.HayRegister()
