#!/usr/bin/env python2
"""
Misc
"""
from __future__ import print_function

import os

from mycpp.mylib import log

from typing import List


def run_tests():
    # type: () -> None

    f = lambda i: i + 1

    dict_comp = {k: 42 for k in [1, 2, 3]}

    set_comp = {k for k in [1, 2, 3]}

    # This is visited as part of list comprehension
    #gen = (x for x in [1, 2, 3])

    exec('x = 42')

    # ok
    assign_to_listcomp = ['t' for s in xrange(5)]

    # Not ok
    mylist = []  # type: List[List[str]]
    mylist.append(['s' for s in xrange(3)])


class A:
    pass


class B:
    pass


class Child(A, B):
    pass


# Doesn't need to be checked, because it fails at runtime
#class Child2('invalid'):
#    pass


def run_benchmarks():
    # type: () -> None
    raise NotImplementedError()


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
