#!/usr/bin/env python2
"""
cast.py - For debugging a problem with StackRoots generation
"""
from __future__ import print_function

import os
from typing import Tuple, cast

from mycpp import mylib
from mycpp.mylib import log


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


def run_tests():
    # type: () -> None
    f = mylib.BufWriter()
    out = ColorOutput(f)
    out.WriteRaw(('yo', 2))
    s, num_chars = out.GetRaw()
    print(s)


def run_benchmarks():
    # type: () -> None
    raise NotImplementedError()


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
