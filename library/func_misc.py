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

        li = pos_args[0]
        UP_li = li

        to_append = pos_args[1]

        with tagswitch(li) as case:
            if case(value_e.BashArray):
                li = cast(value.BashArray, UP_li)
                s = val_ops.ToStr(to_append,
                                  loc.Missing,
                                  prefix='append builtin ')
                li.strs.append(s)

            elif case(value_e.List):
                li = cast(value.List, UP_li)
                li.items.append(to_append)
            else:
                raise error.InvalidType('append() expected List', loc.Missing)

        # Equivalent to no return value?
        return value.Null


class Pop(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        li = pos_args[0]
        UP_li = li

        with tagswitch(li) as case:
            if case(value_e.BashArray):
                li = cast(value.BashArray, UP_li)
                li.strs.pop()

            elif case(value_e.List):
                li = cast(value.List, UP_li)
                li.items.pop()
            else:
                raise error.InvalidType('append() expected List', loc.Missing)

        # Equivalent to no return value?
        return value.Null


class StartsWith(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        reader = typed_args.Reader(pos_args, named_args)
        string = reader.PosStr()
        match = reader.PosStr()
        reader.Done()

        res = string.startswith(match)
        return value.Bool(res)


class Strip(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        reader = typed_args.Reader(pos_args, named_args)
        string = reader.PosStr()
        reader.Done()

        res = string.strip()
        return value.Str(res)


class Upper(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        reader = typed_args.Reader(pos_args, named_args)
        string = reader.PosStr()
        reader.Done()

        res = string.upper()
        return value.Str(res)


class Keys(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        reader = typed_args.Reader(pos_args, named_args)
        dictionary = reader.PosDict()
        reader.Done()

        keys = [value.Str(k) for k in dictionary.keys()]  # type: List[value_t]
        return value.List(keys)


class Len(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        reader = typed_args.Reader(pos_args, named_args)
        x = reader.PosValue()
        reader.Done()

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

        raise error.InvalidType('%s has no length' % value_str(x.tag()), loc.Missing)
