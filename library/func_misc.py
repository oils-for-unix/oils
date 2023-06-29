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
