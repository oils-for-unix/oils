#!/usr/bin/env python2
"""
invalid_assignment.py
"""

from typing import Tuple


def a():
    # type: () -> Tuple[int, int]
    return (1, 2)


def run_tests():
    # type: () -> None

    # OK
    a, b = a()

    # OK
    c = 1, 2

    # NOT OK
    x, y = 1, 2
