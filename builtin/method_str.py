"""YSH Str methods"""

from __future__ import print_function

from _devbuild.gen.value_asdl import (value, value_e, value_t)

from core import error
from core import vm
from frontend import typed_args
from mycpp.mylib import log, tagswitch
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
                capture_names = eggex_val.capture_names
                func_names = eggex_val.func_names

            elif case(value_e.Str):
                ere = cast(value.Str, pattern).s
                cflags = 0
                capture_names = []
                func_names = []

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

        return value.Match(string, indices, capture_names, func_names)
