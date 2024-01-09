"""YSH Str methods"""

from __future__ import print_function

from _devbuild.gen.value_asdl import (value, value_e, value_t, eggex_ops,
                                      eggex_ops_t, RegexMatch)
from core import error
from core import state
from core import vm
from frontend import typed_args
from mycpp.mylib import log, tagswitch
from ysh import expr_eval
from ysh import regex_translate

import libc
from libc import REG_NOTBOL

from typing import cast

_ = log


class StartsWith(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        string = rd.PosStr()
        match = rd.PosStr()
        rd.Done()

        res = string.startswith(match)
        return value.Bool(res)


class Trim(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        string = rd.PosStr()
        rd.Done()

        # TODO: Make this remove unicode spaces
        # Note that we're not calling this function strip() because it doesn't
        # implement Python's whole API.
        # trim() is shorter and it's consistent with JavaScript.
        res = string.strip()
        return value.Str(res)


class Upper(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        string = rd.PosStr()
        rd.Done()

        res = string.upper()
        return value.Str(res)


SEARCH = 0
LEFT_MATCH = 1


class SearchMatch(vm._Callable):

    def __init__(self, which_method):
        # type: (int) -> None
        self.which_method = which_method

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        """
        s => search(eggex, pos=0)
        """
        string = rd.PosStr()

        pattern = rd.PosValue()  # Eggex or ERE Str
        with tagswitch(pattern) as case:
            if case(value_e.Eggex):
                eggex_val = cast(value.Eggex, pattern)

                # lazily converts to ERE
                ere = regex_translate.AsPosixEre(eggex_val)
                cflags = regex_translate.LibcFlags(eggex_val.canonical_flags)
                capture = eggex_ops.Yes(
                    eggex_val.convert_funcs, eggex_val.convert_toks,
                    eggex_val.capture_names)  # type: eggex_ops_t

            elif case(value_e.Str):
                ere = cast(value.Str, pattern).s
                cflags = 0
                capture = eggex_ops.No

            else:
                # TODO: add method name to this error
                raise error.TypeErr(pattern, 'expected Eggex or Str',
                                    rd.LeftParenToken())

        # It's called 'pos', not 'start' like Python.  Python has 2 kinds of
        # 'start' in its regex API, which can be confusing.
        pos = rd.NamedInt('pos', 0)
        rd.Done()

        # Make it anchored
        if self.which_method == LEFT_MATCH and not ere.startswith('^'):
            ere = '^' + ere

        if self.which_method == LEFT_MATCH:
            eflags = 0  # ^ matches beginning even if pos=5
        else:
            eflags = 0 if pos == 0 else REG_NOTBOL  # ^ only matches when pos=0

        indices = libc.regex_search(ere, cflags, string, eflags, pos)

        if indices is None:
            return value.Null

        return RegexMatch(string, indices, capture)


class Replace(vm._Callable):

    def __init__(self, mem, expr_ev):
        # type: (state.Mem, expr_eval.ExprEvaluator) -> None
        self.mem = mem
        self.expr_ev = expr_ev

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        """
        s => replace(match, subst_str, count=0)
        s => replace(eggex, subst_str, count=0)
        s => replace(eggex, subst_expr, count=0)
        """
        string = rd.PosStr()

        string_val = None  # type: value.Str
        eggex_val = None  # type: value.Eggex
        subst_str = None  # type: value.Str
        subst_expr = None  # type: value.Expr

        pattern = rd.PosValue()
        with tagswitch(pattern) as case:
            if case(value_e.Eggex):
                eggex_val = cast(value.Eggex, pattern)

            elif case(value_e.Str):
                string_val = cast(value.Str, pattern)

            else:
                raise error.TypeErr(pattern, 'expected pattern to be Eggex or Str', rd.LeftParenToken())

        subst = rd.PosValue()
        with tagswitch(subst) as case:
            if case(value_e.Str):
                subst_str = cast(value.Str, subst)

            elif case(value_e.Expr):
                subst_expr = cast(value.Expr, subst)

            else:
                raise error.TypeErr(pattern, 'expected substitution to be Str or Expr', rd.LeftParenToken())

        count = rd.NamedInt("count", 0)
        rd.Done()

        if string_val:
            if subst_str:
                return value.Str(string.replace(string_val.s, subst_str.s))

            if subst_expr:
                raise NotImplementedError()

        if eggex_val:
            # lazily converts to ERE
            ere = regex_translate.AsPosixEre(eggex_val)
            cflags = regex_translate.LibcFlags(eggex_val.canonical_flags)

            pos = 0
            while True:
                indices = libc.regex_search(ere, cflags, string, 0, pos)
                if not indices:
                    break

                vars = []
                num_groups = len(indices) / 2
                for group in xrange(num_groups):
                    start = indices[2 * group]
                    end = indices[2 * group + 1]

                    vars.append(string[start:end])

                if subst_str:
                    s = subst_str.s
                if subst_expr:
                    self.mem.argv_stack.append(state._ArgFrame(vars[1:]))
                    UP_res = self.expr_ev.EvalExpr(subst_expr.e, rd.LeftParenToken())
                    with tagswitch(UP_res) as case:
                        if case(value_e.Str):
                            res = cast(value.Str, UP_res)
                            s = res.s
                        else:
                            raise error.TypeErr(UP_res, "expected expr to eval to a string", rd.LeftParenToken())

                start = indices[0]
                end = indices[1]
                string = string[:start] + s + string[end:]

                if len(string) == end + 1:
                    break
                else:
                    pos = end

        return value.Str(string)
