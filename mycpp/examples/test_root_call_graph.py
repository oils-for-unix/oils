#!/usr/bin/env python2
"""
test_root_call_graph.py
"""
from __future__ import print_function

import os

from mycpp import mylib
from mylib import log
from testpkg import module1
from typing import List


def DoesCollect():
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
    DoesCollect()
    print('baz')


def from_import1():
    # type: () -> None
    module1.does_collect('a string')
    print('it worked')


def from_import2(cat):
    # type: (module1.Cat) -> None
    cat.ThingThatCollects()
    print('it worked again')


def FunctionModuleTest():
    # type: () -> None
    DoesCollect()
    bar()
    baz()
    from_import1()
    cat = module1.Cat()
    from_import2(cat)
    module1.does_collect(bar())


def DoWorkThatCollects(item):
    # type: (str) -> None

    mylib.MaybeCollect()


def MainLoop(n):
    # type: (int) -> None

    # Create some strings
    big_list = []  # type: List[str]
    for i in xrange(n):
        # quadratically sized
        big_list.append('loop' * i)

    for i, item in enumerate(big_list):
        if i % 3 == 0:
            big_list[i] = None

        if i % 5 == 0:
            DoWorkThatCollects(item)

    m = 0
    for item in big_list:
        if item is not None:
            m += 1
    print('%d items remaining out of %d' % (m, n))


def VirtualFunctionTest():
    # type: () -> None

    # Not doing virtual functions yet.

    MainLoop(1000)


def run_tests():
    # type: () -> None

    FunctionModuleTest()

    VirtualFunctionTest()



def run_benchmarks():
    # type: () -> None
    pass


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
