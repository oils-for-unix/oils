#!/usr/bin/env python2
"""
val_ops.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, value_e, value_str, value_t
from _devbuild.gen.syntax_asdl import loc

from core import error
from mycpp.mylib import tagswitch

from typing import cast, Optional


def MustBeInt(val):
    # type: (value_t) -> value.Int
    UP_val = val
    if val.tag() == value_e.Int:
        val = cast(value.Int, UP_val)
        return val

    raise error.InvalidType(
        'expected value.Int, but got %s' % value_str(val.tag()), loc.Missing)


def MustBeStr(val):
    # type: (value_t) -> value.Str
    UP_val = val
    if val.tag() == value_e.Str:
        val = cast(value.Str, UP_val)
        return val

    raise error.InvalidType(
        'expected value.Str, but got %s' % value_str(val.tag()), loc.Missing)


def MustBeList(val):
    # type: (value_t) -> value.List
    UP_val = val
    if val.tag() == value_e.List:
        val = cast(value.List, UP_val)
        return val

    raise error.InvalidType(
        'expected value.List, but got %s' % value_str(val.tag()), loc.Missing)


def MustBeFunc(val):
    # type: (value_t) -> value.Func
    UP_val = val
    if val.tag() == value_e.Func:
        val = cast(value.Func, UP_val)
        return val

    raise error.InvalidType(
        'expected value.Func, but got %s' % value_str(val.tag()), loc.Missing)


def Stringify(val):
    # type: (value_t) -> str
    """
    Used by

    $[x]    stringify operator
    @[x]    expression splice - each element is stringified
    @x      splice value
    """
    pass


def ToShellArray(val):
    # type: (value_t) -> str
    """
    Used by

    @[x]  expression splice
    @x    splice value

          Do dictionaries get spliced?
    """
    # iterate and then stringify?
    # It doesn't make sense for Dict because:
    # - keys are already strings
    # - it's not clear you want the keys only?


class Iterator(object):
    """
    Iterate over a single item.  Used by
    
    @myarray              splice
    setvar x, y = y, x    destructured assignment 
    for x in (myval) {    loop
    """

    def __init__(self, val):
        # type: (value_t) -> None
        self.val = val
        self.i = 0

        UP_val = val
        with tagswitch(val) as case:

            if case(value_e.MaybeStrArray):
                val = cast(value.MaybeStrArray, UP_val)
                self.n = len(val.strs)

            elif case(value_e.List):
                val = cast(value.List, UP_val)
                self.n = len(val.items)

            else:
                raise error.InvalidType2(val, 'ItemIterator', loc.Missing)

    def GetNext(self):
        # type: () -> Optional[value_t]

        if self.i == self.n:
            return None

        ret = None  # type: value_t
        val = self.val
        UP_val = val
        with tagswitch(self.val) as case:

            if case(value_e.MaybeStrArray):
                val = cast(value.MaybeStrArray, UP_val)
                ret = value.Str(val.strs[self.i])

            elif case(value_e.List):
                val = cast(value.List, UP_val)
                ret = val.items[self.i]

            else:
                raise error.InvalidType2(val, 'ItemIterator', loc.Missing)

        self.i += 1

        return ret
