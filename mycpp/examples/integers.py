#!/usr/bin/env python2
"""
integers.py
"""
from __future__ import print_function

import os
from mycpp import mylib
from mycpp.mylib import log

from typing import cast


def run_tests():
    # type: () -> None

    a = 3 + 2
    print('a = %d' % a)

    if 0:  # TODO:
        i1 = cast(mylib.BigInt, 1 << 31)  # type: mylib.BigInt
        i2 = mylib.AddBig(i1, i1)
        i3 = mylib.AddBig(i2, i1)

        print('i2 = %d' % i2)
        print('i3 = %d' % i3)


def run_benchmarks():
    # type: () -> None
    pass


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
