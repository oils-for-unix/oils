#!/usr/bin/env python2
"""
invalid_partialtype.py
"""

from typing import Optional


def f():
    # type: () -> int
    return 1


def run_tests():
    # type: () -> None

    # OK
    a = None  # type: Optional[str]
    a = "a"

    # NOT OK
    b = None
    b = f()

    # ALSO NOT OK
    c = None
    c = "c"
