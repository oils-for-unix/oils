#!/usr/bin/env python2
"""
func_misc.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, value_t, value_e
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

        spec = typed_args.Spec([value_e.Str, value_e.Str], {})
        spec.AssertArgs("startswith", pos_args, named_args)

        string = cast(value.Str, pos_args[0]).s
        match = cast(value.Str, pos_args[1]).s

        res = string.startswith(match)
        return value.Bool(res)


class Strip(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        spec = typed_args.Spec([value_e.Str], {})
        spec.AssertArgs("strip", pos_args, named_args)

        string = cast(value.Str, pos_args[0]).s

        res = string.strip()
        return value.Str(res)


class Upper(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        spec = typed_args.Spec([value_e.Str], {})
        spec.AssertArgs("upper", pos_args, named_args)

        string = cast(value.Str, pos_args[0]).s

        res = string.upper()
        return value.Str(res)


class Keys(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        spec = typed_args.Spec([value_e.Dict], {})
        spec.AssertArgs("keys", pos_args, named_args)

        dictionary = cast(value.Dict, pos_args[0]).d

        keys = [value.Str(k) for k in dictionary.keys()]  # type: List[value_t]
        return value.List(keys)
