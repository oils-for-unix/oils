"""
py3_fastfunc.py

Python 3 stub - based on fastfunc.pyi
"""

from typing import Tuple


def J8EncodeString(s, j8_fallback):
    # type: (str, int) -> str
    import json  # hacky stub
    return json.dumps(s)


def ShellEncodeString(s, ysh_fallback):
    # type: (str, int) -> str
    raise NotImplementedError()


def PartIsUtf8(s, start, end):
    # type: (str, int, int) -> bool
    raise NotImplementedError()


def Utf8DecodeOne(s, start):
    # type: (str, int) -> Tuple[int, int]
    raise NotImplementedError()


def CanOmitQuotes(s):
    # type: (str) -> bool
    return False  # stub, everything quoted now?
