#!/usr/bin/env python2
"""
func_misc.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, value_e, value_t
from _devbuild.gen.syntax_asdl import loc
from core import error
from core import vm
from mycpp.mylib import log, tagswitch
from ysh import val_ops

from typing import TYPE_CHECKING, Dict, List, cast

_ = log


class Append(vm._Callable):

    def __init__(self):
        # type: () -> None
        """Empty constructor for mycpp."""
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        li = pos_args[0]
        UP_li = li

        to_append = pos_args[1]

        with tagswitch(li) as case:
            if case(value_e.MaybeStrArray):
                li = cast(value.MaybeStrArray, UP_li)
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
        """Empty constructor for mycpp."""
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        li = pos_args[0]
        UP_li = li

        with tagswitch(li) as case:
            if case(value_e.MaybeStrArray):
                li = cast(value.MaybeStrArray, UP_li)
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
        """Empty constructor for mycpp."""
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        # TODO: add helpers for this?
        if len(pos_args) != 2:
            raise error.InvalidType("startsWith() expects 2 arguments but %d were given" % len(pos_args), loc.Missing)

        if len(named_args) != 0:
            raise error.InvalidType("startsWith() expects 0 named arguments but %d were given" % len(named_args), loc.Missing)

        string = pos_args[0]
        match = pos_args[1]

        assert string.tag() == value_e.Str, "Unreachable, StartsWith is only defined on Str"
        if match.tag() != value_e.Str:
            raise error.InvalidType("startsWith() expected Str", loc.Missing)

        string_s = cast(value.Str, string).s
        match_s = cast(value.Str, match).s

        res = string_s.startswith(match_s)
        return value.Bool(res)


class Strip(vm._Callable):

    def __init__(self):
        # type: () -> None
        """Empty constructor for mycpp."""
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        if len(pos_args) != 1:
            raise error.InvalidType("upper() expects 1 arguments but %d were given" % len(pos_args), loc.Missing)

        if len(named_args) != 0:
            raise error.InvalidType("upper() expects 0 named arguments but %d were given" % len(named_args), loc.Missing)

        string = pos_args[0]

        assert string.tag() == value_e.Str, "Unreachable, Keys is only defined on Str"

        string_s = cast(value.Str, string).s

        res = string_s.strip()
        return value.Str(res)


class Upper(vm._Callable):

    def __init__(self):
        # type: () -> None
        """Empty constructor for mycpp."""
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        if len(pos_args) != 1:
            raise error.InvalidType("upper() expects 1 arguments but %d were given" % len(pos_args), loc.Missing)

        if len(named_args) != 0:
            raise error.InvalidType("upper() expects 0 named arguments but %d were given" % len(named_args), loc.Missing)

        string = pos_args[0]

        assert string.tag() == value_e.Str, "Unreachable, Keys is only defined on Str"

        string_s = cast(value.Str, string).s

        res = string_s.upper()
        return value.Str(res)


class Keys(vm._Callable):

    def __init__(self):
        # type: () -> None
        """Empty constructor for mycpp."""
        pass

    def Call(self, pos_args, named_args):
        # type: (List[value_t], Dict[str, value_t]) -> value_t

        if len(pos_args) != 1:
            raise error.InvalidType("keys() expects 1 arguments but %d were given" % len(pos_args), loc.Missing)

        if len(named_args) != 0:
            raise error.InvalidType("keys() expects 0 named arguments but %d were given" % len(named_args), loc.Missing)

        dictionary = pos_args[0]

        assert dictionary.tag() == value_e.Dict, "Unreachable, Keys is only defined on Dict"

        dictionary_d = cast(value.Dict, dictionary).d

        keys = [value.Str(k) for k in dictionary_d.keys()]  # type: List[value_t]
        return value.List(keys)
