#!/usr/bin/env python2
from __future__ import print_function

from _devbuild.gen.syntax_asdl import source, loc, command_t
from _devbuild.gen.value_asdl import value, cmd_frag
from builtin import hay_ysh
from core import alloc
from core import error
from core import main_loop
from core import state
from display import ui
from core import vm
from frontend import reader
from frontend import typed_args

import posix_ as posix

from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from _devbuild.gen.value_asdl import value_t
    from core import process
    from frontend import parse_lib
    from osh import cmd_eval


class ParseHay(vm._Callable):
    """parseHay()"""

    def __init__(
            self,
            fd_state,  # type:process.FdState
            parse_ctx,  # type: parse_lib.ParseContext
            mem,  # type: state.Mem
            errfmt,  # type: ui.ErrorFormatter
    ):
        # type: (...) -> None
        self.fd_state = fd_state
        self.parse_ctx = parse_ctx
        self.mem = mem
        self.errfmt = errfmt

    def _Call(self, path):
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

        parse_opts = state.MakeYshParseOpts()
        # Note: runtime needs these options and totally different memory

        # TODO: CommandParser needs parse_opts
        c_parser = self.parse_ctx.MakeConfigParser(line_reader)

        # TODO: Should there be a separate config file source?
        src = source.OtherFile(path, call_loc)
        try:
            with alloc.ctx_SourceCode(arena, src):
                node = main_loop.ParseWholeFile(c_parser)
        except error.Parse as e:
            self.errfmt.PrettyPrintError(e)
            return None

        return value.Command(cmd_frag.Expr(node), self.mem.CurrentFrame(),
                             self.mem.GlobalFrame())

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        string = rd.PosStr()
        rd.Done()
        return self._Call(string)


class EvalHay(vm._Callable):
    """evalHay()"""

    def __init__(
            self,
            hay_state,  # type: hay_ysh.HayState
            mutable_opts,  # type: state.MutableOpts
            mem,  # type: state.Mem
            cmd_ev,  #type: cmd_eval.CommandEvaluator
    ):
        # type: (...) -> None
        self.hay_state = hay_state
        self.mutable_opts = mutable_opts
        self.mem = mem
        self.cmd_ev = cmd_ev

    def _Call(self, cmd):
        # type: (command_t) -> Dict[str, value_t]

        with hay_ysh.ctx_HayEval(self.hay_state, self.mutable_opts, self.mem):
            unused = self.cmd_ev.EvalCommandFrag(cmd)

        return self.hay_state.Result()

        # Note: we should discourage the unvalidated top namespace for files?  It
        # needs more validation.

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        cmd = rd.PosCommandFrag()
        rd.Done()
        return value.Dict(self._Call(cmd))


class BlockAsStr(vm._Callable):
    """block_as_str

    TODO:
    - I think this should be cmd->exportAsJson() or something
    - maybe not toJson(), because that's a bit cavalier?
    """

    def __init__(self, arena):
        # type: (alloc.Arena) -> None
        self.arena = arena

    def _Call(self, block):
        # type: (value_t) -> value_t
        return block

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        val = rd.PosValue()
        rd.Done()
        return self._Call(val)


class HayFunc(vm._Callable):
    """_hay() register"""

    def __init__(self, hay_state):
        # type: (hay_ysh.HayState) -> None
        self.hay_state = hay_state

    def _Call(self):
        # type: () -> Dict[str, value_t]
        return self.hay_state.HayRegister()

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        # TODO: check args
        return value.Dict(self._Call())
