#!/usr/bin/env python2
"""
files.py
"""
from __future__ import print_function

import os
import sys

from mycpp import mylib
from mycpp.mylib import log


def run_tests():
    # type: () -> None

    f = mylib.BufWriter()
    for i in xrange(30):
        f.write(chr(i + 65))

    contents = f.getvalue()
    log('Wrote %d bytes to StringIO', len(contents))

    # the f(g(), h()) problem with mark and sweep!!!
    if 1:
        log('contents = %s ... %s', contents[:10], contents[-10:])

    # Does not have the problem
    if 0:
        a = contents[:10]
        b = contents[-10:]
        log('contents = %s ... %s', a, b)

    f2 = mylib.Stdout()
    f2.write('stdout\n')


def run_benchmarks():
    # type: () -> None
    n = 10000

    result = 0

    i = 0
    while i < n:
        f = mylib.BufWriter()
        for j in xrange(30):
            f.write(chr(j + 65))

        result += len(f.getvalue())

        mylib.MaybeCollect()

        i += 1
    log('Ran %d iterations', n)
    log('result = %d', result)


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
