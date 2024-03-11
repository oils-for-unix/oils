#!/usr/bin/env python2
"""
test_cast.py 
"""
from __future__ import print_function

import os
from typing import Tuple, cast

from mycpp import mylib
from mycpp.mylib import log, tagswitch


class ColorOutput(object):
    """Abstract base class for plain text, ANSI color, and HTML color."""

    def __init__(self, f):
        # type: (mylib.Writer) -> None
        self.f = f
        self.num_chars = 0

    def WriteRaw(self, raw):
        # type: (Tuple[str, int]) -> None
        """
        Write raw data without escaping, and without counting control codes in the
        length.
        """
        s, num_chars = raw
        self.f.write(s)
        self.num_chars += num_chars

    def GetRaw(self):
        # type: () -> Tuple[str, int]

        # NOTE: Ensured by NewTempBuffer()
        f = cast(mylib.BufWriter, self.f)
        return f.getvalue(), self.num_chars


def Test1():
    # type: () -> None
    """For debugging a problem with StackRoots generation"""

    f = mylib.BufWriter()
    out = ColorOutput(f)
    out.WriteRaw(('yo', 2))
    s, num_chars = out.GetRaw()
    print(s)


class value_t:

    def __init__(self):
        # type: () -> None
        pass

    def tag(self):
        # type: () -> int
        raise NotImplementedError()


class value__Int(value_t):

    def __init__(self, i):
        # type: (int) -> None
        self.i = i

    def tag(self):
        # type: () -> int
        return 1


class value__Eggex(value_t):

    def __init__(self, ere):
        # type: (str) -> None
        self.ere = ere

    def tag(self):
        # type: () -> int
        return 2


def Test2():
    # type: () -> None

    # Inspired by HasAffix()

    e = value__Eggex('[0-9]+')

    pattern_val = e  # type: value_t

    pattern_eggex = None  # type: value__Eggex
    i = 42
    with tagswitch(pattern_val) as case:
        if case(1):  # Int
            raise AssertionError()
        elif case(2):
            pattern_eggex = cast(value__Eggex, pattern_val)
        else:
            raise AssertionError()

    print('eggex = %r' % pattern_eggex.ere)


def run_tests():
    # type: () -> None

    Test1()
    #Test2()


def run_benchmarks():
    # type: () -> None
    raise NotImplementedError()


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
