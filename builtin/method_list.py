"""Methods on YSH List"""

from __future__ import print_function

from _devbuild.gen.value_asdl import (value, value_t)

from core import num
from core import vm
from frontend import typed_args
from mycpp.mylib import log
from ysh import val_ops

_ = log


class Append(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        items = rd.PosList()
        to_append = rd.PosValue()
        rd.Done()

        items.append(to_append)
        return value.Null


class Extend(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        a = rd.PosList()
        b = rd.PosList()
        rd.Done()

        a.extend(b)
        return value.Null


class Pop(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        items = rd.PosList()
        rd.Done()

        return items.pop()


class Reverse(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        li = rd.PosList()
        rd.Done()

        li.reverse()

        return value.Null


class IndexOf(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        li = rd.PosList()
        needle = rd.PosValue()
        rd.Done()
        i = 0
        while i < len(li):
            if val_ops.ExactlyEqual(li[i], needle, rd.LeftParenToken()):
                return num.ToBig(i)
            i += 1
        return num.ToBig(-1)
