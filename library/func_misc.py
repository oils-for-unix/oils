#!/usr/bin/env python2
"""
func_misc.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, value_str, value_t, value_e
from _devbuild.gen.syntax_asdl import loc
from core import error
from core import vm
from frontend import typed_args
from mycpp.mylib import log, tagswitch
from ysh import val_ops

from typing import TYPE_CHECKING, Dict, List, cast

_ = log


class Append(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        items = r.PosList()
        to_append = r.PosValue()
        r.Done()

        items.append(to_append)

        # Equivalent to no return value?
        return value.Null


class Pop(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        items = r.PosList()
        r.Done()

        items.pop()

        return value.Null


class StartsWith(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        string = r.PosStr()
        match = r.PosStr()
        r.Done()

        res = string.startswith(match)
        return value.Bool(res)


class Strip(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        string = r.PosStr()
        r.Done()

        res = string.strip()
        return value.Str(res)


class Upper(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        string = r.PosStr()
        r.Done()

        res = string.upper()
        return value.Str(res)


class Keys(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        dictionary = r.PosDict()
        r.Done()

        keys = [value.Str(k) for k in dictionary.keys()]  # type: List[value_t]
        return value.List(keys)


class Len(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        x = r.PosValue()
        r.Done()

        UP_x = x
        with tagswitch(x) as case:
            if case(value_e.List):
                x = cast(value.List, UP_x)
                return value.Int(len(x.items))

            elif case(value_e.Dict):
                x = cast(value.Dict, UP_x)
                return value.Int(len(x.d))

            elif case(value_e.Str):
                x = cast(value.Str, UP_x)
                return value.Int(len(x.s))

        raise error.TypeErr(x, 'len() expected Str, List, or Dict',
                            loc.Missing)


class Join(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        li = r.PosList()

        delim = ''
        if len(pos_args): # reader has a reference
            delim = r.PosStr()

        r.Done()

        strs = []  # type: List[str]
        for i, el in enumerate(li):
            strs.append(val_ops.Stringify(el, loc.Missing))

        return value.Str(delim.join(strs))


class Maybe(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        r = typed_args.Reader(pos_args, named_args)
        val = r.PosValue()
        r.Done()

        if val == value.Null:
            return value.List([])

        s = val_ops.ToStr(
            val, 'maybe() expected Str, but got %s' % value_str(val.tag()),
            loc.Missing)
        if len(s):
            return value.List([val])  # use val to avoid needlessly copy

        return value.List([])
