#!/usr/bin/env python2
"""
The subset of Lib/locale.py we use, with type annotations

That wraps Modules/_localemodule.c aka _locale.so
"""
from __future__ import print_function

import _locale  # type: ignore

CODESET = _locale.CODESET  # type: int
LC_CTYPE = _locale.LC_CTYPE  # type: int


class Error(Exception):
    pass


def setlocale(category, locale):
    # type: (int, str) -> str
    try:
        return _locale.setlocale(category, locale)  # type: ignore
    except _locale.Error:
        raise Error()


def nl_langinfo(item):
    # type: (int) -> str
    return _locale.nl_langinfo(item)  # type: ignore
