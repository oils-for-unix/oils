#!/usr/bin/env python2
"""
classes.py - Test out inheritance.
"""
from __future__ import print_function

import cStringIO
import os
import sys

from mycpp import mylib
from mycpp.mylib import log

from typing import List, cast

# Based on asdl/format.py


class AnObject(object):
    """Abstract base class for plain text, ANSI color, and HTML color."""

    def __init__(self, l):
        # type: (List[str]) -> None
        self.strs = l


def Leaker(some_strs):
    # type: (List[str]) -> AnObject
    return AnObject(some_strs)


def TestEscape1():
    # type: () -> None

    leaked = [] # type: List[str]
    an_obj = AnObject(leaked)

    not_leaked = [] # type: List[int]
    for i in xrange(1, 1000):
        not_leaked.append(i)


def TestEscape2():
    # type: () -> None
    a_list = [] # type: List[str]
    leaky = [] # type: List[str]
    hole = Leaker(a_list)
    hole.strs = leaky
    an_alias = hole.strs


def run_tests():
    # type: () -> None

    TestEscape1()
    TestEscape2()


def run_benchmarks():
    # type: () -> None

    pass


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()

# vim: sw=2

