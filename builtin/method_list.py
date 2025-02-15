"""Methods on YSH List"""

from __future__ import print_function

from _devbuild.gen.value_asdl import (value, value_t)

from core import num
from core import vm
from frontend import typed_args
from mycpp import mops
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


class Clear(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        li = rd.PosList()
        rd.Done()

        del li[:]

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
        return value.Int(mops.MINUS_ONE)


class LastIndexOf(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        li = rd.PosList()
        needle = rd.PosValue()
        rd.Done()

        i = len(li) - 1
        while i > -1:
            if val_ops.ExactlyEqual(li[i], needle, rd.LeftParenToken()):
                return num.ToBig(i)
            i -= 1
        return value.Int(mops.MINUS_ONE)


class Remove(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        li = rd.PosList()
        to_remove = rd.PosValue()
        rd.Done()

        i = 0
        while i < len(li):
            if val_ops.ExactlyEqual(li[i], to_remove, rd.LeftParenToken()):
                li.pop(i)
                return value.Null
            i += 1
        return value.Null

class Insert(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        li = rd.PosList()
        at_index = mops.BigTruncate(rd.PosInt())  # List limited to 2^32 entries
        to_insert = rd.PosValue()
        rd.Done()

        i = len(li)
        if at_index < 0:
            if at_index < -(i + 1): # clamp -ve index to minimum -ve value
                at_index = -(i + 1)
            at_index = i + at_index + 1  # Turn -ve index into equivalent +ve index

        # Add extra item at the end
        li.append(None)

        # Shift everything
        while i > at_index:
            li[i] = li[i-1]
            i -= 1
        li[i] = to_insert

        return value.Null
