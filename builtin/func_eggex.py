#!/usr/bin/env python2
"""
func_eggex.py
"""
from __future__ import print_function

from _devbuild.gen.syntax_asdl import loc_t, Token
from _devbuild.gen.value_asdl import (value, value_e, value_t, eggex_ops,
                                      eggex_ops_e, eggex_ops_t, regex_match_e,
                                      RegexMatch)
from core import error
from core import state
from core import vm
from frontend import typed_args
from mycpp.mylib import log, tagswitch

from typing import Optional, cast, TYPE_CHECKING
if TYPE_CHECKING:
    from ysh.expr_eval import ExprEvaluator

_ = log

G = 0  # _group()
S = 1  # _start()
E = 2  # _end()


class _MatchCallable(vm._Callable):

    def __init__(self, to_return, expr_ev):
        # type: (int, Optional[ExprEvaluator]) -> None
        self.to_return = to_return
        self.expr_ev = expr_ev

    def _ReturnValue(self, match, group_index, blame_loc):
        # type: (RegexMatch, int, loc_t) -> value_t
        num_groups = len(match.indices) / 2  # including group 0
        if group_index < num_groups:
            start = match.indices[2 * group_index]
            if self.to_return == S:
                return value.Int(start)

            end = match.indices[2 * group_index + 1]
            if self.to_return == E:
                return value.Int(end)

            if start == -1:
                return value.Null
            else:
                val = value.Str(match.s[start:end])  # type: value_t

                convert_func = None  # type: Optional[value_t]
                convert_tok = None  # type: Optional[Token]
                with tagswitch(match.ops) as case:
                    if case(eggex_ops_e.Yes):
                        ops = cast(eggex_ops.Yes, match.ops)

                        # group 0 doesn't have a name or type attached to it
                        if len(ops.convert_funcs) and group_index != 0:
                            convert_func = ops.convert_funcs[group_index - 1]
                            convert_tok = ops.convert_toks[group_index - 1]

                if convert_func is not None:
                    assert convert_tok is not None
                    # Blame the group() call?  It would be nicer to blame the
                    # Token re.Capture.func_name, but we lost that in
                    # _EvalEggex()
                    val = self.expr_ev.CallConvertFunc(convert_func, val,
                                                       convert_tok, blame_loc)

                return val
        else:
            assert num_groups != 0
            raise error.Expr(
                'Expected capture group less than %d, got %d' %
                (num_groups, group_index), blame_loc)

    def _Call(self, match, group_arg, blame_loc):
        # type: (RegexMatch, value_t, loc_t) -> value_t
        group_index = _GetGroupIndex(group_arg, match.ops, blame_loc)
        return self._ReturnValue(match, group_index, blame_loc)


def _GetGroupIndex(group, ops, blame_loc):
    # type: (value_t, eggex_ops_t, loc_t) -> int
    UP_group = group

    with tagswitch(group) as case:
        if case(value_e.Int):
            group = cast(value.Int, UP_group)
            group_index = group.i

        elif case(value_e.Str):
            group = cast(value.Str, UP_group)

            UP_ops = ops
            with tagswitch(ops) as case2:
                if case2(eggex_ops_e.No):
                    raise error.Expr(
                        "ERE captures don't have names (%r)" % group.s,
                        blame_loc)
                elif case2(eggex_ops_e.Yes):
                    ops = cast(eggex_ops.Yes, UP_ops)
                    group_index = -1
                    for i, name in enumerate(ops.capture_names):
                        if name == group.s:
                            group_index = i + 1  # 1-based
                            break
                    if group_index == -1:
                        raise error.Expr('No such group %r' % group.s,
                                         blame_loc)

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

        match = self.mem.GetRegexMatch()
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
