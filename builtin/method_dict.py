"""Methods on YSH Dict"""

from __future__ import print_function

from _devbuild.gen.value_asdl import (value, value_e, value_t, Obj)

from core import error
from core import vm
from frontend import typed_args
from mycpp import mylib
from mycpp.mylib import log, tagswitch

from typing import cast, List

_ = log


class Keys(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        dictionary = rd.PosDict()
        rd.Done()

        keys = [value.Str(k) for k in dictionary.keys()]  # type: List[value_t]
        return value.List(keys)


class Values(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        dictionary = rd.PosDict()
        rd.Done()

        values = dictionary.values()  # type: List[value_t]
        return value.List(values)


class Erase(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        dictionary = rd.PosDict()
        key = rd.PosStr()
        rd.Done()

        mylib.dict_erase(dictionary, key)
        return value.Null


class Get(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        obj = rd.PosValue()
        key = rd.PosStr()
        default_value = rd.PosValue()
        rd.Done()

        UP_obj = obj
        with tagswitch(obj) as case:
            if case(value_e.Dict):
                obj = cast(value.Dict, UP_obj)
                d = obj.d
            elif case(value_e.Obj):
                obj = cast(Obj, UP_obj)
                d = obj.d
            else:
                raise error.TypeErr(obj, 'get() expected Dict or Obj',
                                    rd.BlamePos())

        return d.get(key, default_value)
