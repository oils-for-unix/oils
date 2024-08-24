"""YSH Str methods"""

from __future__ import print_function

from _devbuild.gen.syntax_asdl import loc_t
from _devbuild.gen.value_asdl import (value, value_e, value_t, eggex_ops,
                                      eggex_ops_t, RegexMatch)
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

from typing import cast, Dict, List, Tuple

_ = log


def _StrMatchStart(s, p):
    # type: (str, str) -> Tuple[bool, int, int]
    """Returns the range of bytes in 's' that match string pattern `p`. the
    pattern matches if 's' starts with all the characters in 'p'.

    The returned match result is the tuple "(matched, begin, end)". 'matched'
    is true if the pattern matched. 'begin' and 'end' give the half-open range
    "[begin, end)" of byte indices from 's' for the match, and are a valid but
    empty range if 'match' is false.

    Used for shell functions like 'trimStart' when trimming a prefix string.
    """
    if s.startswith(p):
        return (True, 0, len(p))
    else:
        return (False, 0, 0)


def _StrMatchEnd(s, p):
    # type: (str, str) -> Tuple[bool, int, int]
    """Returns a match result for the bytes in 's' that match string pattern
    `p`. the pattern matches if 's' ends with all the characters in 'p'.

    The returned match result is the tuple "(matched, begin, end)". 'matched'
    is true if the pattern matched. 'begin' and 'end' give the half-open range
    "[begin, end)" of byte indices from 's' for the match, and are a valid but
    empty range if 'match' is false.

    Used for shell functions like 'trimEnd' when trimming a suffix string.
    """
    len_s = len(s)
    if s.endswith(p):
        return (True, len_s - len(p), len_s)
    else:
        return (False, len_s, len_s)


def _EggexMatchCommon(s, p, ere, empty_p):
    # type: (str, value.Eggex, str, int) -> Tuple[bool, int, int]
    cflags = regex_translate.LibcFlags(p.canonical_flags)
    eflags = 0
    indices = libc.regex_search(ere, cflags, s, eflags)
    if indices is None:
        return (False, empty_p, empty_p)

    start = indices[0]
    end = indices[1]

    return (True, start, end)


def _EggexMatchStart(s, p):
    # type: (str, value.Eggex) -> Tuple[bool, int, int]
    """Returns a match result for the bytes in 's' that match Eggex pattern
    `p` when constrained to match at the start of the string.

    Any capturing done by the Eggex pattern is ignored.

    The returned match result is the tuple "(matched, begin, end)". 'matched'
    is true if the pattern matched. 'begin' and 'end' give the half-open range
    "[begin, end)" of byte indices from 's' for the match, and are a valid but
    empty range if 'match' is false.

    Used for shell functions like 'trimStart' when trimming with an Eggex
    pattern.
    """
    ere = regex_translate.AsPosixEre(p)
    if not ere.startswith('^'):
        ere = '^' + ere
    return _EggexMatchCommon(s, p, ere, 0)


def _EggexMatchEnd(s, p):
    # type: (str, value.Eggex) -> Tuple[bool, int, int]
    """Like _EggexMatchStart, but matches against the end of the
    string.
    """
    ere = regex_translate.AsPosixEre(p)
    if not ere.endswith('$'):
        ere = ere + '$'
    return _EggexMatchCommon(s, p, ere, len(s))


START = 0b01
END = 0b10


class HasAffix(vm._Callable):
    """ Implements `startsWith()`, `endsWith()`. """

    def __init__(self, anchor):
        # type: (int) -> None
        assert anchor in (START, END), ("Anchor must be START or END")
        self.anchor = anchor

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        """
        string => startsWith(pattern_str)   # => bool
        string => startsWith(pattern_eggex) # => bool
        string => endsWith(pattern_str)     # => bool
        string => endsWith(pattern_eggex)   # => bool
        """

        string = rd.PosStr()
        pattern_val = rd.PosValue()
        pattern_str = None  # type: str
        pattern_eggex = None  # type: value.Eggex
        with tagswitch(pattern_val) as case:
            if case(value_e.Eggex):
                pattern_eggex = cast(value.Eggex, pattern_val)
            elif case(value_e.Str):
                pattern_str = cast(value.Str, pattern_val).s
            else:
                raise error.TypeErr(pattern_val,
                                    'expected pattern to be Eggex or Str',
                                    rd.LeftParenToken())
        rd.Done()

        matched = False
        try:
            if pattern_str is not None:
                if self.anchor & START:
                    matched, _, _ = _StrMatchStart(string, pattern_str)
                else:
                    matched, _, _ = _StrMatchEnd(string, pattern_str)
            else:
                assert pattern_eggex is not None
                if self.anchor & START:
                    matched, _, _ = _EggexMatchStart(string, pattern_eggex)
                else:
                    matched, _, _ = _EggexMatchEnd(string, pattern_eggex)
        except error.Strict as e:
            raise error.Expr(e.msg, e.location)

        return value.Bool(matched)


class Trim(vm._Callable):
    """ Implements `trimStart()`, `trimEnd()`, and `trim()` """

    def __init__(self, anchor):
        # type: (int) -> None
        assert anchor in (START, END, START
                          | END), ("Anchor must be START, END, or START|END")
        self.anchor = anchor

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        """
        string => trimStart()               # => Str
        string => trimEnd()                 # => Str
        string => trim()                    # => Str
        string => trimStart(pattern_str)    # => Str
        string => trimEnd(pattern_str)      # => Str
        string => trim(pattern_str)         # => Str
        string => trimStart(pattern_eggex)  # => Str
        string => trimEnd(pattern_eggex)    # => Str
        string => trim(pattern_eggex)       # => Str
        """

        string = rd.PosStr()
        pattern_val = rd.OptionalValue()
        pattern_str = None  # type: str
        pattern_eggex = None  # type: value.Eggex
        if pattern_val:
            with tagswitch(pattern_val) as case:
                if case(value_e.Eggex):
                    pattern_eggex = cast(value.Eggex, pattern_val)
                elif case(value_e.Str):
                    pattern_str = cast(value.Str, pattern_val).s
                else:
                    raise error.TypeErr(pattern_val,
                                        'expected pattern to be Eggex or Str',
                                        rd.LeftParenToken())
        rd.Done()

        start = 0
        end = len(string)
        try:
            if pattern_str is not None:
                if self.anchor & START:
                    _, _, start = _StrMatchStart(string, pattern_str)
                if self.anchor & END:
                    _, end, _ = _StrMatchEnd(string, pattern_str)
            elif pattern_eggex is not None:
                if self.anchor & START:
                    _, _, start = _EggexMatchStart(string, pattern_eggex)
                if self.anchor & END:
                    _, end, _ = _EggexMatchEnd(string, pattern_eggex)
            else:
                if self.anchor & START:
                    _, start = string_ops.StartsWithWhitespaceByteRange(string)
                if self.anchor & END:
                    end, _ = string_ops.EndsWithWhitespaceByteRange(string)
        except error.Strict as e:
            raise error.Expr(e.msg, e.location)

        res = string[start:end]
        return value.Str(res)


class Upper(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        s = rd.PosStr()
        rd.Done()

        # TODO: unicode support
        return value.Str(s.upper())


class Lower(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t

        s = rd.PosStr()
        rd.Done()

        # TODO: unicode support
        return value.Str(s.lower())


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
                with state.ctx_Eval(self.mem, string_val.s, None, None):
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
                named_vars = {}  # type: Dict[str, value_t]
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
                            named_vars[name] = val

                if subst_str:
                    s = subst_str.s
                if subst_expr:
                    with state.ctx_Eval(self.mem, arg0, argv, named_vars):
                        s = self.EvalSubstExpr(subst_expr, rd.LeftParenToken())
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


class Split(vm._Callable):

    def __init__(self):
        # type: () -> None
        pass

    def Call(self, rd):
        # type: (typed_args.Reader) -> value_t
        """
        s.split(delim, count=-1)
        s.split(eggex, count=-1)

        Count behaves like in replace() in that:
        - `count` <  0 -> ignore
        - `count` >= 0 -> there will be at most `count` splits
        """
        string = rd.PosStr()

        string_sep = None  # type: str
        eggex_sep = None  # type: value.Eggex

        sep = rd.PosValue()
        with tagswitch(sep) as case:
            if case(value_e.Eggex):
                eggex_sep_ = cast(value.Eggex, sep)
                eggex_sep = eggex_sep_

            elif case(value_e.Str):
                string_sep_ = cast(value.Str, sep)
                string_sep = string_sep_.s

            else:
                raise error.TypeErr(sep, 'expected sep to be Eggex or Str',
                                    rd.LeftParenToken())

        count = mops.BigTruncate(rd.NamedInt("count", -1))
        rd.Done()

        if len(string) == 0:
            return value.List([])

        if string_sep is not None:
            if len(string_sep) == 0:
                raise error.Structured(3, "sep must be non-empty",
                                       rd.LeftParenToken())

            cursor = 0
            chunks = []  # type: List[value_t]
            while cursor < len(string) and count != 0:
                next = string.find(string_sep, cursor)
                if next == -1:
                    break

                chunks.append(value.Str(string[cursor:next]))
                cursor = next + len(string_sep)
                count -= 1

            chunks.append(value.Str(string[cursor:]))

            return value.List(chunks)

        if eggex_sep is not None:
            if '\0' in string:
                raise error.Structured(3, "cannot split a string with a NUL byte",
                                       rd.LeftParenToken())

            regex = regex_translate.AsPosixEre(eggex_sep)
            cflags = regex_translate.LibcFlags(eggex_sep.canonical_flags)

            zero_width_match = libc.regex_search(regex, cflags, "", 0)
            if zero_width_match is not None:
                raise error.Structured(3, "cannot split by eggex which accepts the empty string", rd.LeftParenToken())

            cursor = 0
            chunks = []
            while cursor < len(string) and count != 0:
                m = libc.regex_search(regex, cflags, string, 0, cursor)
                if m is None:
                    break

                start = m[0]
                end = m[1]
                assert start != end, "We should have guarded against zero-width matches"

                chunks.append(value.Str(string[cursor:start]))
                cursor = end

                count -= 1

            chunks.append(value.Str(string[cursor:]))

            return value.List(chunks)

        raise AssertionError()

