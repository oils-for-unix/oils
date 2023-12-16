"""Methods on various types"""

from __future__ import print_function

from _devbuild.gen.value_asdl import (value, value_t)

from builtin import func_eggex
from core import state
from core import vm
from frontend import typed_args
from mycpp.mylib import log

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


class MatchAccess(vm._Callable):

    def __init__(self, to_return):
        # type: (int) -> None
        self.to_return = to_return

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        # This is guaranteed
        m = rd.PosMatch()
        # TODO: Support strings for named captures
        i = rd.OptionalInt(default_=0)
        #val = rd.PosValue()

        rd.Done()

        return func_eggex.GetMatch(m.s, m.indices, i, self.to_return,
                                   rd.LeftParenToken())
