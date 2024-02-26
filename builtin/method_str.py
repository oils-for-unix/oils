"""YSH Str methods"""

from __future__ import print_function

from _devbuild.gen.syntax_asdl import loc_t, loc
from _devbuild.gen.runtime_asdl import scope_e
from _devbuild.gen.value_asdl import (value, value_e, value_t, eggex_ops,
                                      eggex_ops_t, RegexMatch, LeftName)
from builtin import pure_ysh
from core import error
from core import state
from core import vm
from frontend import typed_args
from mycpp import mops
from mycpp.mylib import log, tagswitch
from osh import string_ops
from ysh import expr_eval
from ysh import regex_translate
from ysh import val_ops

import libc
from libc import REG_NOTBOL

from typing import cast, Any, List, Optional, Tuple

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


# From https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Lexical_grammar#white_space
SPACES = [0x0009,  # Horizontal tab (\t)
          0x000A,  # Newline (\n)
          0x000B,  # Vertical tab (\v)
          0x000C,  # Form feed (\f)
          0x000D,  # Carriage return (\r)
          0x0020,  # Normal space
          0x00A0,  # No-break space 	<NBSP>
          0xFEFF]  # Zero-width no-break space <ZWNBSP>


def _IsSpace(codepoint):
    # type: (int) -> bool
    return codepoint in SPACES


TRIM_LEFT = 1
TRIM_RIGHT = 2
TRIM_BOTH = 3


class Trim(vm._Callable):

    def __init__(self, trim):
        # type: (int) -> None
        self.trim = trim

    def _Left(self, string):
        # type: (str) -> int
        i = 0
        while i < len(string):
            codepoint = string_ops.DecodeUtf8Char(string, i)
            if not _IsSpace(codepoint):
                break

            try:
                i = string_ops.NextUtf8Char(string, i)
            except error.Strict as e:
                raise error.Expr(e.msg, e.location)

        return i

    def _Right(self, string):
        # type: (str) -> int
        i = len(string)
        while i > 0:
            try:
                prev = string_ops.PreviousUtf8Char(string, i)
            except error.Strict as e:
                raise error.Expr(e.msg, e.location)

            codepoint = string_ops.DecodeUtf8Char(string, prev)
            if not _IsSpace(codepoint):
                break

            i = prev

        return i

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        string = rd.PosStr()
        rd.Done()

        left = 0
        right = len(string)
        if self.trim & TRIM_LEFT:
            left = self._Left(string)
        if self.trim & TRIM_RIGHT:
            right = self._Right(string)

        res = string[left:right]
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
        pos = mops.BigTruncate(rd.NamedInt('pos', 0))
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


class ctx_EvalReplace(object):
    """For $0, $1, $2, $3, ... replacements in Str => replace()"""

    def __init__(self, mem, arg0, argv):
        # type: (state.Mem, str, Optional[List[str]]) -> None
        # argv will be None for Str => replace(Str, Expr)
        if argv is None:
            self.pushed_argv = False
        else:
            mem.argv_stack.append(state._ArgFrame(argv))
            self.pushed_argv = True

        # $0 needs to have lexical scoping. So we store it with other locals.
        # As "0" cannot be parsed as an lvalue, we can safely store arg0 there.
        assert mem.GetValue("0", scope_e.LocalOnly).tag() == value_e.Undef
        self.lval = LeftName("0", loc.Missing)
        mem.SetLocalName(self.lval, value.Str(arg0))

        self.mem = mem

    def __enter__(self):
        # type: () -> None
        pass

    def __exit__(self, type, value_, traceback):
        # type: (Any, Any, Any) -> None
        self.mem.SetLocalName(self.lval, value.Undef)
        if self.pushed_argv:
            self.mem.argv_stack.pop()


class Replace(vm._Callable):

    def __init__(self, mem, expr_ev):
        # type: (state.Mem, expr_eval.ExprEvaluator) -> None
        self.mem = mem
        self.expr_ev = expr_ev

    def EvalSubstExpr(self, expr, blame_loc):
        # type: (value.Expr, loc_t) -> str
        res = self.expr_ev.EvalExpr(expr.e, blame_loc)
        if res.tag() == value_e.Str:
            return cast(value.Str, res).s

        raise error.TypeErr(res, "expected expr to eval to a Str", blame_loc)

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        """
        s => replace(string_val, subst_str, count=-1)
        s => replace(string_val, subst_expr, count=-1)
        s => replace(eggex_val, subst_str, count=-1)
        s => replace(eggex_val, subst_expr, count=-1)

        For count in [0, MAX_INT], there will be no more than count
        replacements. Any negative count should read as unset, and replace will
        replace all occurances of the pattern.
        """
        string = rd.PosStr()

        string_val = None  # type: value.Str
        eggex_val = None  # type: value.Eggex
        subst_str = None  # type: value.Str
        subst_expr = None  # type: value.Expr

        pattern = rd.PosValue()
        with tagswitch(pattern) as case:
            if case(value_e.Eggex):
                # HACK: mycpp will otherwise generate:
                #  value::Eggex* eggex_val ...
                eggex_val_ = cast(value.Eggex, pattern)
                eggex_val = eggex_val_

            elif case(value_e.Str):
                string_val_ = cast(value.Str, pattern)
                string_val = string_val_

            else:
                raise error.TypeErr(pattern,
                                    'expected pattern to be Eggex or Str',
                                    rd.LeftParenToken())

        subst = rd.PosValue()
        with tagswitch(subst) as case:
            if case(value_e.Str):
                subst_str_ = cast(value.Str, subst)
                subst_str = subst_str_

            elif case(value_e.Expr):
                subst_expr_ = cast(value.Expr, subst)
                subst_expr = subst_expr_

            else:
                raise error.TypeErr(subst,
                                    'expected substitution to be Str or Expr',
                                    rd.LeftParenToken())

        count = mops.BigTruncate(rd.NamedInt("count", -1))
        rd.Done()

        if count == 0:
            return value.Str(string)

        if string_val:
            if subst_str:
                s = subst_str.s
            if subst_expr:
                # Eval with $0 set to string_val (the matched substring)
                with ctx_EvalReplace(self.mem, string_val.s, None):
                    s = self.EvalSubstExpr(subst_expr, rd.LeftParenToken())
            assert s is not None

            result = string.replace(string_val.s, s, count)

            return value.Str(result)

        if eggex_val:
            ere = regex_translate.AsPosixEre(eggex_val)
            cflags = regex_translate.LibcFlags(eggex_val.canonical_flags)

            # Walk through the string finding all matches of the compiled ere.
            # Then, collect unmatched substrings and substitutions into the
            # `parts` list.
            pos = 0
            parts = []  # type: List[str]
            replace_count = 0
            while pos < len(string):
                indices = libc.regex_search(ere, cflags, string, 0, pos)
                if indices is None:
                    break

                # Collect captures
                arg0 = None  # type: str
                argv = []  # type: List[str]
                named_vars = []  # type: List[Tuple[str, value_t]]
                num_groups = len(indices) / 2
                for group in xrange(num_groups):
                    start = indices[2 * group]
                    end = indices[2 * group + 1]
                    captured = string[start:end]
                    val = value.Str(captured)  # type: value_t

                    if len(eggex_val.convert_funcs) and group != 0:
                        convert_func = eggex_val.convert_funcs[group - 1]
                        convert_tok = eggex_val.convert_toks[group - 1]

                        if convert_func:
                            val = self.expr_ev.CallConvertFunc(
                                convert_func, val, convert_tok,
                                rd.LeftParenToken())

                    # $0, $1, $2 variables are argv values, which must be
                    # strings. Furthermore, they can only be used in string
                    # contexts
                    #   eg. "$[1]" != "$1".
                    val_str = val_ops.Stringify(val, rd.LeftParenToken())
                    if group == 0:
                        arg0 = val_str
                    else:
                        argv.append(val_str)

                    # $0 cannot be named
                    if group != 0:
                        name = eggex_val.capture_names[group - 2]
                        if name is not None:
                            named_vars.append((name, val))

                if subst_str:
                    s = subst_str.s
                if subst_expr:
                    with ctx_EvalReplace(self.mem, arg0, argv):
                        with pure_ysh.ctx_Shvar(self.mem, named_vars):
                            s = self.EvalSubstExpr(subst_expr,
                                                   rd.LeftParenToken())
                assert s is not None

                start = indices[0]
                end = indices[1]
                parts.append(string[pos:start])  # Unmatched substring
                parts.append(s)  # Replacement
                pos = end  # Move to end of match

                replace_count += 1
                if count != -1 and replace_count == count:
                    break

            parts.append(string[pos:])  # Remaining unmatched substring

            return value.Str("".join(parts))

        raise AssertionError()
