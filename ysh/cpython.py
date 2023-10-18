#!/usr/bin/env python2
"""
cpython.py - temporary bridge
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import (
    value,
    value_e,
    value_t,
)
from _devbuild.gen.syntax_asdl import loc
from core import error
from core import vm
from mycpp.mylib import log, NewDict, tagswitch

from typing import cast, Any, Dict, List

_ = log


# XXX this function should be removed once _EvalExpr is completeley refactored.
# Until then we'll need this as a bit of scaffolding to allow us to refactor one
# kind of expression at a time while still being able to type-check and run
# tests.
def _PyObjToValue(val):
    # type: (Any) -> value_t

    if val is None:
        return value.Null

    elif isinstance(val, bool):
        return value.Bool(val)

    elif isinstance(val, int):
        return value.Int(val)

    elif isinstance(val, float):
        return value.Float(val)

    elif isinstance(val, str):
        return value.Str(val)

    elif isinstance(val, list):
        # Hack for converting back and forth
        is_shell_array = True

        shell_array = []  # type: List[str]
        typed_array = []  # type: List[value_t]

        for elem in val:
            if elem is None:
                shell_array.append(elem)
                typed_array.append(value.Null)

            elif isinstance(elem, str):
                shell_array.append(elem)
                typed_array.append(value.Str(elem))

            elif isinstance(elem, value_t):  # Does this happen?
                is_shell_array = False
                typed_array.append(elem)

            else:
                is_shell_array = False
                typed_array.append(_PyObjToValue(elem))
                #typed_array.append(elem)

        #if is_shell_array:
        #    return value.BashArray(shell_array)
        return value.List(typed_array)

    elif isinstance(val, xrange):
        # awkward, but should go away once everything is typed...
        l = list(val)
        if len(l) > 1:
            return value.Range(l[0], l[-1])

        # Empty range
        return value.Range(0, 0)

    elif isinstance(val, dict):
        is_shell_dict = True

        shell_dict = NewDict()  # type: Dict[str, str]
        typed_dict = NewDict()  # type: Dict[str, value_t]

        for k, v in val.items():
            if isinstance(v, str):
                shell_dict[k] = v
                typed_dict[k] = value.Str(v)

            elif isinstance(v, value_t):  # Does this happen?
                is_shell_dict = False
                typed_dict[k] = v

            else:
                is_shell_dict = False
                typed_dict[k] = _PyObjToValue(v)
                #typed_dict[k] = v

        if is_shell_dict:
            return value.BashAssoc(shell_dict)
        else:
            return value.Dict(typed_dict)

    elif isinstance(val, value.Eggex):
        return val  # passthrough

    elif isinstance(val, value.Command):
        return val  # passthrough

    elif isinstance(val, vm._Callable) or callable(val):
        raise AssertionError()

    else:
        raise error.Expr(
            'Trying to convert unexpected type to value_t: %r' % val,
            loc.Missing)


def _ValueToPyObj(val):
    # type: (value_t) -> Any

    if not isinstance(val, value_t):
        raise AssertionError(val)

    UP_val = val
    with tagswitch(val) as case:
        if case(value_e.Null):
            return None

        elif case(value_e.Undef):
            return None

        elif case(value_e.Bool):
            val = cast(value.Bool, UP_val)
            return val.b

        elif case(value_e.Int):
            val = cast(value.Int, UP_val)
            return val.i

        elif case(value_e.Float):
            val = cast(value.Float, UP_val)
            return val.f

        elif case(value_e.Str):
            val = cast(value.Str, UP_val)
            return val.s

        elif case(value_e.BashArray):
            val = cast(value.BashArray, UP_val)
            return val.strs

        elif case(value_e.List):
            val = cast(value.List, UP_val)
            return list(map(_ValueToPyObj, val.items))

        elif case(value_e.BashAssoc):
            val = cast(value.BashAssoc, UP_val)
            return val.d

        elif case(value_e.Dict):
            val = cast(value.Dict, UP_val)
            d = NewDict()  # type: Dict[str, value_t]
            for k, v in val.d.items():
                d[k] = _ValueToPyObj(v)
            return d

        elif case(value_e.Eggex):
            return val  # passthrough

        elif case(value_e.Range):
            val = cast(value.Range, UP_val)
            return xrange(val.lower, val.upper)

        elif case(value_e.BuiltinFunc):
            val = cast(value.BuiltinFunc, UP_val)
            return val.callable

        elif case(value_e.Command):
            return val  # passthrough

        else:
            raise error.Expr(
                'Trying to convert unexpected type to pyobj: %r' % val,
                loc.Missing)
