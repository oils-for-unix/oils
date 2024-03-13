#!/usr/bin/env python2
from __future__ import print_function

import os
from mycpp.mylib import log


def f(s):
    # type: (str) -> str
    return s[1].upper()


def run_tests():
    # type: () -> None

    #a = 'foo' + 'bar'
    a = 'food'
    print(a.upper())

    print(f(a))


def run_benchmarks():
    # type: () -> None
    pass


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
