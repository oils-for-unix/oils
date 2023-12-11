"""Methods on various types"""

from __future__ import print_function

from _devbuild.gen.value_asdl import (value, value_t)

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


# which method group() start() end()
GROUP = 0
START = 1
END = 2

class MatchAccess(vm._Callable):

    def __init__(self, method):
        # type: (int) -> None
        self.method = method

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        # This is guaranteed
        m = rd.PosMatch()

        # string name or integer
        val = rd.PosValue()
        rd.Done()

        # TODO: look at m.indices and return a string

        return value.Null
