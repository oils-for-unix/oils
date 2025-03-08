"""Methods on various types"""

from __future__ import print_function

from _devbuild.gen.value_asdl import (value, value_t, LiteralBlock, cmd_frag,
                                      cmd_frag_e)

from core import alloc
from core import num
from core import state
from core import vm
from display import ui
from frontend import typed_args
from mycpp.mylib import log, tagswitch, NewDict

from typing import Dict, Optional, cast

_ = log


class SetValue(vm._Callable):

    def __init__(self, mem):
        # type: (state.Mem) -> None
        self.mem = mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        # This is guaranteed
        place = rd.PosPlace()

        val = rd.PosValue()
        rd.Done()

        self.mem.SetPlace(place, val, rd.LeftParenToken())

        return value.Null


class SourceCode(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        # This is guaranteed
        cmd = rd.PosCommand()
        rd.Done()

        # For now, we only have lines if the block arg is literal like p { echo
        # hi }
        # As opposed to
        # p (; ; myblock)

        lit_block = None  # type: Optional[LiteralBlock]
        frag = cmd.frag
        with tagswitch(frag) as case:
            if case(cmd_frag_e.LiteralBlock):
                lit_block = cast(LiteralBlock, frag)
            elif case(cmd_frag_e.Expr):
                c = cast(cmd_frag.Expr, frag).c
                return value.Null
            else:
                raise AssertionError()

        result = NewDict()  # type: Dict[str, value_t]

        brace_group = lit_block.brace_group
        # BraceGroup has location for {
        line = brace_group.left.line

        # for the user to pass back to --location-str
        result['location_str'] = value.Str(ui.GetLineSourceString(line))
        result['location_start_line'] = num.ToBig(line.line_num)

        #log('LINES %s', lit_block.lines)
        # Between { and }
        code_str = alloc.SnipCodeBlock(brace_group.left, brace_group.right,
                                       lit_block.lines)

        result['code_str'] = value.Str(code_str)

        return value.Dict(result)
