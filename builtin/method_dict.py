"""Methods on YSH Dict"""

from __future__ import print_function

from _devbuild.gen.value_asdl import (value, value_e, value_t, Obj)
from _devbuild.gen.runtime_asdl import coerced_e

from core import error
from core import vm
from frontend import typed_args
from mycpp import mylib, mops
from mycpp.mylib import log, tagswitch
from ysh import expr_eval

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


class Clear(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        dictionary = rd.PosDict()
        rd.Done()

        dictionary.clear()
        return value.Null


class Inc(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        dictionary = rd.PosDict()
        key = rd.PosStr()
        inc_val = rd.PosValue()
        rd.Done()

        # default value for the dictionary entry is zero
        if key in dictionary:
            left = dictionary[key]
        else:
            left = value.Int(mops.ZERO)

        c, i1, i2, f1, f2 = expr_eval.ConvertForBinaryOp(left, inc_val)

        if c == coerced_e.Int:
            res = value.Int(mops.Add(i1, i2))  # type: value_t
        elif c == coerced_e.Float:
            res = value.Float(f1 + f2)
        else:
            raise error.TypeErr(left, 'inc() expected Int/Float value in dict',
                                rd.BlamePos())

        dictionary[key] = res

        return value.Null


class Append(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        dictionary = rd.PosDict()
        key = rd.PosStr()
        append_val = rd.PosValue()
        rd.Done()

        if key in dictionary:
            UP_obj = dictionary[key]
            if UP_obj.tag() == value_e.List:
                lst = cast(value.List, UP_obj)
                lst.items.append(append_val)
            else:
                raise error.TypeErr(UP_obj, 'append() expected List value in dict',
                                    rd.BlamePos())
        else:
            dictionary[key] = value.List([append_val])

        return value.Null


class Get(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        obj = rd.PosValue()
        key = rd.PosStr()
        default_value = rd.OptionalValue()
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

        if default_value is None:
            default_value = value.Null
        return d.get(key, default_value)
