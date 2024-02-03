#!/usr/bin/env python2
"""
val_ops.py
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import loc, loc_t, command_t
from _devbuild.gen.value_asdl import (value, value_e, value_t, eggex_ops,
                                      eggex_ops_t, regex_match, RegexMatch)
from core import error
from core import ui
from mycpp.mylib import tagswitch
from ysh import regex_translate

from typing import TYPE_CHECKING, cast, Dict, List, Optional

import libc

if TYPE_CHECKING:
    from core import state


def ToInt(val, msg, blame_loc):
    # type: (value_t, str, loc_t) -> int
    UP_val = val
    if val.tag() == value_e.Int:
        val = cast(value.Int, UP_val)
        return val.i

    raise error.TypeErr(val, msg, blame_loc)


def ToFloat(val, msg, blame_loc):
    # type: (value_t, str, loc_t) -> float
    UP_val = val
    if val.tag() == value_e.Float:
        val = cast(value.Float, UP_val)
        return val.f

    raise error.TypeErr(val, msg, blame_loc)


def ToStr(val, msg, blame_loc):
    # type: (value_t, str, loc_t) -> str
    UP_val = val
    if val.tag() == value_e.Str:
        val = cast(value.Str, UP_val)
        return val.s

    raise error.TypeErr(val, msg, blame_loc)


def ToList(val, msg, blame_loc):
    # type: (value_t, str, loc_t) -> List[value_t]
    UP_val = val
    if val.tag() == value_e.List:
        val = cast(value.List, UP_val)
        return val.items

    raise error.TypeErr(val, msg, blame_loc)


def ToDict(val, msg, blame_loc):
    # type: (value_t, str, loc_t) -> Dict[str, value_t]
    UP_val = val
    if val.tag() == value_e.Dict:
        val = cast(value.Dict, UP_val)
        return val.d

    raise error.TypeErr(val, msg, blame_loc)


def ToCommand(val, msg, blame_loc):
    # type: (value_t, str, loc_t) -> command_t
    UP_val = val
    if val.tag() == value_e.Command:
        val = cast(value.Command, UP_val)
        return val.c

    raise error.TypeErr(val, msg, blame_loc)


def Stringify(val, blame_loc, prefix=''):
    # type: (value_t, loc_t, str) -> str
    """
    Used by

    $[x]    stringify operator
    @[x]    expression splice - each element is stringified
    @x      splice value
    """
    if blame_loc is None:
        blame_loc = loc.Missing

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

        elif case(value_e.List):
            raise error.TypeErrVerbose(
                "%sgot a List, which can't be stringified. Perhaps use @ instead of $, or use join()"
                % prefix, blame_loc)

        else:
            raise error.TypeErr(
                val, "%sexpected Null, Bool, Int, Float, Eggex" % prefix,
                blame_loc)

    return s


def ToShellArray(val, blame_loc, prefix=''):
    # type: (value_t, loc_t, str) -> List[str]
    """
    Used by

    @[x]  expression splice
    @x    splice value

    Dicts do NOT get spliced, but they iterate over their keys
    So this function NOT use Iterator.
    """
    UP_val = val
    with tagswitch(val) as case2:
        if case2(value_e.List):
            val = cast(value.List, UP_val)
            strs = []  # type: List[str]
            # Note: it would be nice to add the index to the error message
            # prefix, WITHOUT allocating a string for every item
            for item in val.items:
                strs.append(Stringify(item, blame_loc, prefix=prefix))

        # I thought about getting rid of this to keep OSH and YSH separate,
        # but:
        # - readarray/mapfile returns bash array (ysh-user-feedback depends on it)
        # - ysh-options tests parse_at too
        elif case2(value_e.BashArray):
            val = cast(value.BashArray, UP_val)
            strs = val.strs

        else:
            raise error.TypeErr(val, "%sexpected List" % prefix, blame_loc)

    return strs


class _ContainerIter(object):
    """Interface for various types of for loop."""

    def __init__(self):
        # type: () -> None
        self.i = 0

    def Index(self):
        # type: () -> int
        return self.i

    def Next(self):
        # type: () -> None
        self.i += 1

    def Done(self):
        # type: () -> int
        raise NotImplementedError()

    def FirstValue(self):
        # type: () -> value_t
        """Return Dict key or List value"""
        raise NotImplementedError()

    def SecondValue(self):
        # type: () -> value_t
        """Return Dict value or FAIL"""
        raise AssertionError("Shouldn't have called this")


class ArrayIter(_ContainerIter):
    """ for x in 1 2 3 { """

    def __init__(self, strs):
        # type: (List[str]) -> None
        _ContainerIter.__init__(self)
        self.strs = strs
        self.n = len(strs)

    def Done(self):
        # type: () -> int
        return self.i == self.n

    def FirstValue(self):
        # type: () -> value_t
        return value.Str(self.strs[self.i])


class RangeIterator(_ContainerIter):
    """ for x in (m:n) { """

    def __init__(self, val):
        # type: (value.Range) -> None
        _ContainerIter.__init__(self)
        self.val = val

    def Done(self):
        # type: () -> int
        return self.val.lower + self.i >= self.val.upper

    def FirstValue(self):
        # type: () -> value_t
        return value.Int(self.val.lower + self.i)


class ListIterator(_ContainerIter):
    """ for x in (mylist) { """

    def __init__(self, val):
        # type: (value.List) -> None
        _ContainerIter.__init__(self)
        self.val = val
        self.n = len(val.items)

    def Done(self):
        # type: () -> int
        return self.i == self.n

    def FirstValue(self):
        # type: () -> value_t
        return self.val.items[self.i]


class DictIterator(_ContainerIter):
    """ for x in (mydict) { """

    def __init__(self, val):
        # type: (value.Dict) -> None
        _ContainerIter.__init__(self)

        # TODO: Don't materialize these Lists
        self.keys = val.d.keys()  # type: List[str]
        self.values = val.d.values()  # type: List[value_t]

        self.n = len(val.d)
        assert self.n == len(self.keys)

    def Done(self):
        # type: () -> int
        return self.i == self.n

    def FirstValue(self):
        # type: () -> value_t
        return value.Str(self.keys[self.i])

    def SecondValue(self):
        # type: () -> value_t
        return self.values[self.i]


def ToBool(val):
    # type: (value_t) -> bool
    """Convert any value to a boolean.

    TODO: expose this as Bool(x), like Python's bool(x).
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
        elif case(value_e.BashArray):
            val = cast(value.BashArray, UP_val)
            return len(val.strs) != 0

        elif case(value_e.BashAssoc):
            val = cast(value.BashAssoc, UP_val)
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


def ExactlyEqual(left, right, blame_loc):
    # type: (value_t, value_t, loc_t) -> bool
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
            # Note: could provide floatEquals(), and suggest it
            # Suggested idiom is abs(f1 - f2) < 0.1
            raise error.TypeErrVerbose("Equality isn't defined on Float",
                                       blame_loc)

        elif case(value_e.Str):
            left = cast(value.Str, UP_left)
            right = cast(value.Str, UP_right)
            return left.s == right.s

        elif case(value_e.BashArray):
            left = cast(value.BashArray, UP_left)
            right = cast(value.BashArray, UP_right)
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
                if not ExactlyEqual(left.items[i], right.items[i], blame_loc):
                    return False

            return True

        elif case(value_e.BashAssoc):
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
                if (k not in right.d or
                        not ExactlyEqual(right.d[k], left.d[k], blame_loc)):
                    return False

            return True

    raise error.TypeErrVerbose(
        "Can't compare two values of type %s" % ui.ValType(left), blame_loc)


def Contains(needle, haystack):
    # type: (value_t, value_t) -> bool
    """Haystack must be a Dict.

    We should have mylist->find(x) !== -1 for searching through a List.
    Things with different perf characteristics should look different.
    """
    UP_haystack = haystack
    with tagswitch(haystack) as case:
        if case(value_e.Dict):
            haystack = cast(value.Dict, UP_haystack)
            s = ToStr(needle, "LHS of 'in' should be Str", loc.Missing)
            return s in haystack.d

        else:
            raise error.TypeErr(haystack, "RHS of 'in' should be Dict",
                                loc.Missing)

    return False


def MatchRegex(left, right, mem):
    # type: (value_t, value_t, Optional[state.Mem]) -> bool
    """
    Args:
      mem: Whether to set or clear matches
    """
    UP_right = right

    with tagswitch(right) as case:
        if case(value_e.Str):  # plain ERE
            right = cast(value.Str, UP_right)

            right_s = right.s
            regex_flags = 0
            capture = eggex_ops.No  # type: eggex_ops_t

        elif case(value_e.Eggex):
            right = cast(value.Eggex, UP_right)

            right_s = regex_translate.AsPosixEre(right)
            regex_flags = regex_translate.LibcFlags(right.canonical_flags)
            capture = eggex_ops.Yes(right.convert_funcs, right.convert_toks,
                                    right.capture_names)

        else:
            raise error.TypeErr(right, 'Expected Str or Regex for RHS of ~',
                                loc.Missing)

    UP_left = left
    left_s = None  # type: str
    with tagswitch(left) as case:
        if case(value_e.Str):
            left = cast(value.Str, UP_left)
            left_s = left.s
        else:
            raise error.TypeErrVerbose('LHS must be a string', loc.Missing)

    indices = libc.regex_search(right_s, regex_flags, left_s, 0)
    if indices is not None:
        if mem:
            mem.SetRegexMatch(RegexMatch(left_s, indices, capture))
        return True
    else:
        if mem:
            mem.SetRegexMatch(regex_match.No)
        return False


# vim: sw=4
