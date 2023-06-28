#!/usr/bin/env python2
"""
val_ops.py
"""
from __future__ import print_function

from _devbuild.gen.runtime_asdl import value, value_e, value_str, value_t
from _devbuild.gen.syntax_asdl import loc

from core import error
from mycpp.mylib import tagswitch
from ysh import regex_translate

from typing import TYPE_CHECKING, cast, Optional

import libc

if TYPE_CHECKING:
    from core import state


def ToInt(val):
    # type: (value_t) -> int
    UP_val = val
    if val.tag() == value_e.Int:
        val = cast(value.Int, UP_val)
        return val.i

    raise error.InvalidType(
        'expected value.Int, but got %s' % value_str(val.tag()), loc.Missing)


def ToStr(val):
    # type: (value_t) -> str
    UP_val = val
    if val.tag() == value_e.Str:
        val = cast(value.Str, UP_val)
        return val.s

    raise error.InvalidType(
        'expected value.Str, but got %s' % value_str(val.tag()), loc.Missing)


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
    UP_val = val
    with tagswitch(val) as case:
        if case(value_e.Str):  # trivial case
            val = cast(value.Str, UP_val)
            return val.s

        elif case(value_e.Null):
            s = 'null'  # JSON spelling

        elif case(value_e.Bool):
            val = cast(value.Bool, UP_val)
            s = 'true' if val.b else 'false'  # JSON spelling

        elif case(value_e.Int):
            val = cast(value.Int, UP_val)
            s = str(val.i)  # Decimal '42', the only sensible representation

        elif case(value_e.Float):
            val = cast(value.Float, UP_val)
            # TODO: what precision does this have?
            # The default could be like awk or Python, and then we also allow
            # ${myfloat %.3f} and more.
            # Python 3 seems to give a few more digits than Python 2 for str(1.0/3)
            s = str(val.f)

        elif case(value_e.Eggex):
            val = cast(value.Eggex, UP_val)
            s = regex_translate.AsPosixEre(val)  # lazily converts to ERE

        else:
            raise error.InvalidType2(
                val, "stringify expected Null, Bool, Int, Float, Eggex",
                loc.Missing)

    return s


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


def ToBool(val):
    # type: (value_t) -> bool
    """Convert any value to a boolean.

    TODO: expose this as Bool(x), like Python's
    bool(x).
    """
    UP_val = val
    with tagswitch(val) as case:
        if case(value_e.Undef):
            return False

        elif case(value_e.Null):
            return False

        elif case(value_e.Str):
            val = cast(value.Str, UP_val)
            return len(val.s) != 0

        # OLD TYPES
        elif case(value_e.MaybeStrArray):
            val = cast(value.MaybeStrArray, UP_val)
            return len(val.strs) != 0

        elif case(value_e.AssocArray):
            val = cast(value.AssocArray, UP_val)
            return len(val.d) != 0

        elif case(value_e.Bool):
            val = cast(value.Bool, UP_val)
            return val.b

        elif case(value_e.Int):
            val = cast(value.Int, UP_val)
            return val.i != 0

        elif case(value_e.Float):
            val = cast(value.Float, UP_val)
            return val.f != 0.0

        elif case(value_e.List):
            val = cast(value.List, UP_val)
            return len(val.items) > 0

        elif case(value_e.Dict):
            val = cast(value.Dict, UP_val)
            return len(val.d) > 0

        else:
            return True  # all other types are Truthy


def ExactlyEqual(left, right):
    # type: (value_t, value_t) -> bool
    if left.tag() != right.tag():
        return False

    UP_left = left
    UP_right = right
    with tagswitch(left) as case:
        if case(value_e.Undef):
            return True  # there's only one Undef

        elif case(value_e.Null):
            return True  # there's only one Null

        elif case(value_e.Bool):
            left = cast(value.Bool, UP_left)
            right = cast(value.Bool, UP_right)
            return left.b == right.b

        elif case(value_e.Int):
            left = cast(value.Int, UP_left)
            right = cast(value.Int, UP_right)
            return left.i == right.i

        elif case(value_e.Float):
            left = cast(value.Float, UP_left)
            right = cast(value.Float, UP_right)
            return left.f == right.f

        elif case(value_e.Str):
            left = cast(value.Str, UP_left)
            right = cast(value.Str, UP_right)
            return left.s == right.s

        elif case(value_e.MaybeStrArray):
            left = cast(value.MaybeStrArray, UP_left)
            right = cast(value.MaybeStrArray, UP_right)
            if len(left.strs) != len(right.strs):
                return False

            for i in xrange(0, len(left.strs)):
                if left.strs[i] != right.strs[i]:
                    return False

            return True

        elif case(value_e.List):
            left = cast(value.List, UP_left)
            right = cast(value.List, UP_right)
            if len(left.items) != len(right.items):
                return False

            for i in xrange(0, len(left.items)):
                if not ExactlyEqual(left.items[i], right.items[i]):
                    return False

            return True

        elif case(value_e.AssocArray):
            left = cast(value.Dict, UP_left)
            right = cast(value.Dict, UP_right)
            if len(left.d) != len(right.d):
                return False

            for k in left.d.keys():
                if k not in right.d or right.d[k] != left.d[k]:
                    return False

            return True

        elif case(value_e.Dict):
            left = cast(value.Dict, UP_left)
            right = cast(value.Dict, UP_right)
            if len(left.d) != len(right.d):
                return False

            for k in left.d.keys():
                if k not in right.d or not ExactlyEqual(right.d[k], left.d[k]):
                    return False

            return True

    raise NotImplementedError(left)


def Contains(needle, haystack):
    # type: (value_t, value_t) -> bool
    """Haystack must be a collection type."""

    UP_needle = needle
    UP_haystack = haystack
    with tagswitch(haystack) as case:
        if case(value_e.List):
            haystack = cast(value.List, UP_haystack)
            for item in haystack.items:
                if ExactlyEqual(item, needle):
                    return True

            return False

        elif case(value_e.MaybeStrArray):
            haystack = cast(value.MaybeStrArray, UP_haystack)
            if needle.tag() != value_e.Str:
                raise error.InvalidType('Expected Str', loc.Missing)

            needle = cast(value.Str, UP_needle)
            for s in haystack.strs:
                if s == needle.s:
                    return True

            return False

        elif case(value_e.Dict):
            haystack = cast(value.Dict, UP_haystack)
            if needle.tag() != value_e.Str:
                raise error.InvalidType('Expected Str', loc.Missing)

            needle = cast(value.Str, UP_needle)
            return needle.s in haystack.d

        elif case(value_e.AssocArray):
            haystack = cast(value.AssocArray, UP_haystack)
            if needle.tag() != value_e.Str:
                raise error.InvalidType('Expected Str', loc.Missing)

            needle = cast(value.Str, UP_needle)
            return needle.s in haystack.d

        else:
            raise error.InvalidType('Expected List or Dict', loc.Missing)

    return False


def RegexMatch(left, right, mem):
    # type: (value_t, value_t, Optional[state.Mem]) -> bool
    """
    Args:
      mem: Whether to set or clear matches
    """
    UP_right = right
    right_s = None  # type: str
    with tagswitch(right) as case:
        if case(value_e.Str):
            right = cast(value.Str, UP_right)
            right_s = right.s
        elif case(value_e.Eggex):
            right = cast(value.Eggex, UP_right)
            right_s = regex_translate.AsPosixEre(right)
        else:
            raise error.InvalidType2(right,
                                     'Expected Str or Regex for RHS of ~',
                                     loc.Missing)

    UP_left = left
    left_s = None  # type: str
    with tagswitch(left) as case:
        if case(value_e.Str):
            left = cast(value.Str, UP_left)
            left_s = left.s
        else:
            raise error.InvalidType('LHS must be a string', loc.Missing)

    # TODO:
    # - libc_regex_match should populate _start() and _end() too (out params?)
    # - What is the ordering for named captures?  See demo/ere*.sh

    matches = libc.regex_match(right_s, left_s)
    if matches is not None:
        if mem:
            mem.SetMatches(matches)
        return True
    else:
        if mem:
            mem.ClearMatches()
        return False
