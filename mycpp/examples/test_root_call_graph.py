#!/usr/bin/env python2
"""
container_types.py
"""
from __future__ import print_function

import os

from mycpp import mylib
from mylib import log
from testpkg import module1
from typing import List


def foo():
    # type: () -> None
    s = 'foo'
    f = [] # type: List[str]
    for i in xrange(1000):
        f.append('a')

    mylib.MaybeCollect()
    print(f[1])
    print(s)


def bar():
    # type: () -> str
    print('bar')
    return 'it works?'


def baz():
    # type: () -> None
    foo()
    print('baz')


def from_import1():
    # type: () -> None
    module1.does_collect('a string')
    print('it worked')


def from_import2(cat):
    # type: (module1.Cat) -> None
    cat.ThingThatCollects()
    print('it worked again')


def run_tests():
    # type: () -> None

    foo()
    bar()
    baz()
    from_import1()
    cat = module1.Cat()
    from_import2(cat)
    module1.does_collect(bar())


def run_benchmarks():
    # type: () -> None
    pass


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
