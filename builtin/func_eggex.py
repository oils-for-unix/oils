#!/usr/bin/env python2
"""
func_eggex.py
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import loc_t
from _devbuild.gen.value_asdl import value, value_e, value_t
from core import error
from core import state
from core import vm
from frontend import typed_args
from mycpp.mylib import log, tagswitch

from typing import List, Optional, cast

_ = log

G = 0  # _match() _group()
S = 1  # _start()
E = 2  # _end()


def _GetMatch(s, indices, i, to_return, blame_loc):
    # type: (str, List[int], int, int, loc_t) -> value_t
    num_groups = len(indices) / 2  # including group 0
    if i < num_groups:
        start = indices[2 * i]
        if to_return == S:
            return value.Int(start)

        end = indices[2 * i + 1]
        if to_return == E:
            return value.Int(end)

        if start == -1:
            return value.Null
        else:
            # TODO: Can apply type conversion function
            # See osh/prompt.py:
            # val = self.expr_ev.PluginCall(func_val, pos_args)
            return value.Str(s[start:end])
    else:
        if num_groups == 0:
            msg = 'No regex capture groups'
        else:
            msg = 'Expected capture group less than %d, got %d' % (num_groups,
                                                                   i)
        raise error.Expr(msg, blame_loc)


def _GetGroupIndex(group, capture_names, blame_loc):
    # type: (value_t, List[Optional[str]], loc_t) -> int
    UP_group = group

    with tagswitch(group) as case:
        if case(value_e.Int):
            group = cast(value.Int, UP_group)
            group_index = group.i

        elif case(value_e.Str):
            group = cast(value.Str, UP_group)
            group_index = -1
            for i, name in enumerate(capture_names):
                if name == group.s:
                    group_index = i + 1  # 1-based
                    break
            if group_index == -1:
                raise error.Expr('No such group %r' % group.s, blame_loc)
        else:
            # TODO: add method name to this error
            raise error.TypeErr(group, 'expected Int or Str', blame_loc)
    return group_index


class MatchFunc(vm._Callable):
    """
    _group(i)
    _start(i)
    _end(i)

    _group(0)             : get the whole match
    _group(1) to _group(N): get a submatch
    _group('month')       : get group by name

    Ditto for _start() and _end()
    """

    def __init__(self, mem, to_return):
        # type: (state.Mem, int) -> None
        vm._Callable.__init__(self)
        self.mem = mem
        self.to_return = to_return

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        group = rd.PosValue()
        rd.Done()

        s, indices, capture_names = self.mem.GetRegexIndices()
        group_index = _GetGroupIndex(group, capture_names, rd.LeftParenToken())

        return _GetMatch(s, indices, group_index, self.to_return,
                         rd.LeftParenToken())


class MatchMethod(vm._Callable):
    """
    m => group(i)
    m => start(i)
    m => end(i)
    """

    def __init__(self, to_return):
        # type: (int) -> None
        self.to_return = to_return

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        # This is guaranteed
        m = rd.PosMatch()
        group = rd.PosValue()
        rd.Done()

        group_index = _GetGroupIndex(group, m.capture_names,
                                     rd.LeftParenToken())

        return _GetMatch(m.s, m.indices, group_index, self.to_return,
                         rd.LeftParenToken())


# vim: sw=4
