#!/usr/bin/env python2
"""
length.py
"""
from __future__ import print_function

import os
from mycpp.mylib import log
from mycpp import mylib

from typing import Optional


def TestMaybeStrEquals():
    # type: () -> None

    a = 'foo'
    b = 'bar'

    y = 'foo'  # type: Optional[str]
    n = None  # type: Optional[str]

    log('a == b  ->  %d', a == b)
    log('a != b  ->  %d', a != b)

    log('a == y  ->  %d', a == y)
    log('a != y  ->  %d', a != y)

    log('a == n  ->  %d', a == n)
    log('a != n  ->  %d', a != n)


def run_tests():
    # type: () -> None
    mystr = 'abcd'
    log("len(mystr) = %d", len(mystr))
    log("mystr[1] = %s", mystr[1])
    log("mystr[1:] = %s", mystr[1:])
    log("mystr[1:3] = %s", mystr[1:3])
    log("mystr[:-2] = %s", mystr[:-2])

    for c in mystr:
        if c == 'b':
            continue
        log('c = %s', c)
        if c == 'c':
            break

    log("")

    # NOTE: Not implementing mylist[:n] or mylist[:-1]  (negative) until I see
    # usages.
    mylist = ['w', 'x', 'y', 'z']
    log("len(mylist) = %d", len(mylist))
    log("mylist[1] = %s", mylist[1])

    # can't print lists directly
    log("len(mylist[1:]) = %d", len(mylist[1:]))

    for c in mylist:
        if c == 'x':
            continue
        log('c = %s', c)
        if c == 'y':
            break

    # to test nullptr.  Python correctly infers this as 'str'
    c2 = None  # type: Optional[str]
    for c2 in mystr:
        if c2 != 'a':  # test != operator
            log('%s != a', c2)

    log('')

    TestMaybeStrEquals()


def run_benchmarks():
    # type: () -> None
    n = 1000000

    mystr = 'abcd'
    mylist = ['w', 'x', 'y', 'z']

    result = 0
    i = 0
    while i < n:
        # C++ has a big advantage here
        #result += len(mystr)
        #result += len(mylist)

        # C++ shows no real advantage here
        result += len(mystr[1:])
        result += len(mylist[1:])

        i += 1

        mylib.MaybeCollect()

    log('result = %d', result)
    log('iterations = %d', n)


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
