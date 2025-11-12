#!/usr/bin/env python2
"""
Unreachable code
"""

def a():
    # type: () -> None
    return
    c = 1


def b():
    # type: () -> None
    raise AssertionError()
    d = 1
