#!/usr/bin/env python2
"""
container_types.py
"""
from __future__ import print_function

import os
from mycpp import mylib
from mycpp.mylib import log

from typing import List, Tuple


def IfDemo(i):
    # type: (int) -> None

    if i == 1:
        print('one')
    elif i == 2:
        print('two')
    elif i == 3:
        print('three')
    elif i == 4:
        pass  # no-op
    else:
        print('other number')


class ParseError(Exception):

    def __init__(self, reason):
        # type: (str) -> None
        self.reason = reason


def f(s):
    # type: (str) -> str

    if s[0] == 'f':
        raise ParseError('started with f')
    return s


def ExceptDemo():
    # type: () -> None

    result = ''
    tmp = ['foo', 'bar']
    for prog in tmp:
        try:
            result = f(prog)
        except ParseError as e:
            log('error: %s', e.reason)
            continue
        log('result = %s', result)


def run_tests():
    # type: () -> None

    tmp = [1, 2, 3, 4, 5]
    for i in tmp:
        IfDemo(i)

    log('')
    ExceptDemo()


def run_benchmarks():
    # type: () -> None

    # BUG: we only get 8191 exceptions instead of 100,000?  I think this must be
    # because of 'throw Alloc<ParseError>?  TODO: Should exceptions throw by
    # value?
    n = 100000

    # C++ exceptions are slower than Python!  Woah.

    result = ''
    num_exceptions = 0
    i = 0

    # Even one failure makes C++ slower!  Otherwise it's faster.
    cases = ['fail', 'ok', 'ok', 'ok']

    # 870 ms in C++, 366 ms in Python
    #cases = ['fail', 'fail', 'fail', 'fail']

    # 26 ms in C++, 70 ms in Python
    # OK it is inverted!  Exceptions are really expensive.
    #cases = ['ok', 'ok', 'ok', 'ok']

    while i < n:
        for prog in cases:
            try:
                result = f(prog)
            except ParseError as e:
                num_exceptions += 1
                continue
        i += 1

        mylib.MaybeCollect()  # manual GC point

    log('num_exceptions = %d', num_exceptions)
    log('Ran %d iterations of try/except', n)


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
