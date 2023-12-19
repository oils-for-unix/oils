#!/usr/bin/env python2
"""
func_eggex.py
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import loc_t
from _devbuild.gen.value_asdl import (value, value_e, value_t, regex_match_e,
                                      RegexMatch)
from core import error
from core import state
from core import vm
from frontend import typed_args
from mycpp.mylib import log, tagswitch

from typing import List, Optional, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from ysh.expr_eval import ExprEvaluator

_ = log

G = 0  # _match() _group()
S = 1  # _start()
E = 2  # _end()


class _MatchCallable(vm._Callable):

    def __init__(self, to_return, expr_ev):
        # type: (int, Optional[ExprEvaluator]) -> None
        self.to_return = to_return
        self.expr_ev = expr_ev

    def _ReturnValue(self, s, indices, i, convert_func, blame_loc):
        # type: (str, List[int], int, Optional[value_t], loc_t) -> value_t
        num_groups = len(indices) / 2  # including group 0
        if i < num_groups:
            start = indices[2 * i]
            if self.to_return == S:
                return value.Int(start)

            end = indices[2 * i + 1]
            if self.to_return == E:
                return value.Int(end)

            if start == -1:
                return value.Null
            else:
                val = value.Str(s[start:end])  # type: value_t
                if convert_func:
                    # Blame the group() call?  It would be nicer to blame the
                    # Token re.Capture.func_name, but we lost that in
                    # _EvalEggex()
                    val = self.expr_ev.CallConvertFunc(convert_func, val,
                                                       blame_loc)
                return val
        else:
            assert num_groups != 0
            msg = 'Expected capture group less than %d, got %d' % (num_groups,
                                                                   i)
            raise error.Expr(msg, blame_loc)

    def _Call(self, match, group_arg, blame_loc):
        # type: (RegexMatch, value_t, loc_t) -> value_t
        group_index = _GetGroupIndex(group_arg, match.capture_names,
                                     blame_loc)

        convert_func = None  # type: Optional[value_t]
        if len(match.convert_funcs):  # for ERE string, it's []
            if group_index != 0:  # doesn't have a name or type attached to it
                convert_func = match.convert_funcs[group_index - 1]

        return self._ReturnValue(match.s, match.indices, group_index,
                                 convert_func, blame_loc)



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


class MatchFunc(_MatchCallable):
    """
    _group(i)
    _start(i)
    _end(i)

    _group(0)             : get the whole match
    _group(1) to _group(N): get a submatch
    _group('month')       : get group by name

    Ditto for _start() and _end()
    """

    def __init__(self, to_return, expr_ev, mem):
        # type: (int, Optional[ExprEvaluator], state.Mem) -> None
        _MatchCallable.__init__(self, to_return, expr_ev)
        self.mem = mem

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        group_arg = rd.PosValue()
        rd.Done()

        match = self.mem.GetRegexIndices()
        UP_match = match
        with tagswitch(match) as case:
            if case(regex_match_e.No):
                # _group(0) etc. is illegal
                raise error.Expr('No regex capture groups',
                                 rd.LeftParenToken())

            elif case(regex_match_e.Yes):
                match = cast(RegexMatch, UP_match)

                return self._Call(match, group_arg, rd.LeftParenToken())

        raise AssertionError()


class MatchMethod(_MatchCallable):
    """
    m => group(i)
    m => start(i)
    m => end(i)
    """

    def __init__(self, to_return, expr_ev):
        # type: (int, Optional[ExprEvaluator]) -> None
        _MatchCallable.__init__(self, to_return, expr_ev)

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        # This is guaranteed
        match = rd.PosMatch()
        group_arg = rd.PosValue()
        rd.Done()

        return self._Call(match, group_arg, rd.LeftParenToken())


# vim: sw=4
