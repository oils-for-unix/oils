#!/usr/bin/env python2
"""
loops.py: Common loops
"""
from __future__ import print_function

import os

from mycpp import mylib
from mycpp.mylib import log, iteritems

from typing import Dict


def TestListComp():
    # type: () -> None
    log('--- list comprehension')

    x = [1, 2, 3, 4]

    y = [i * 5 for i in x[1:]]

    log("len = %d", len(y))
    log("y[0] = %d", y[0])
    log("y[-1] = %d", y[-1])

    log('--- list comprehension changing type')

    z = ['[%d]' % i for i in x[1:-1]]

    # I think this rewrite might be necessary?
    #tmp1 = x[1:-1]
    #z = ['[%d]' % i for i in tmp1]

    if mylib.PYTHON:
        #log("z = %s", z)
        pass

    log("len = %d", len(z))
    log("z[0] = %s", z[0])
    log("z[-1] = %s", z[-1])

    log('-- list comprehension tuple unpacking')

    pairs = [('one', 1), ('two', 2)]

    # Note: listcomp_iter_var is at TOP level, but it could be SCOPED.  It is
    # also rooted at the top level.
    first = [listcomp_iter_var for listcomp_iter_var, _ in pairs]

    for s2 in first:
        log('first = %s', s2)

    log('-- list comprehension filtering')

    parts = ['a', None, 'b']
    tmp = [s for s in parts if s is not None]
    print(''.join(tmp))

    tmp2 = [s for s in tmp if s.startswith('-')]
    print(''.join(tmp2))


def TestDict():
    # type: () -> None
    log('--- Dict')
    d = {}  # type: Dict[str, int]
    d['a'] = 99
    d['c'] = 42
    d['b'] = 0

    log('a = %d', d['a'])
    log('b = %d', d['b'])
    log('c = %d', d['c'])

    for k in d:
        log("k = %s", k)

    for k, v in iteritems(d):
        log("k = %s, v = %d", k, v)


CATS = ['big', 'small', 'hairless']


def TestForLoop():
    # type: () -> None
    log('--- iterate over bytes in string')
    for ch in 'abc':
        log('ch = %s', ch)

    log('--- iterate over items in list')
    for item in ['xx', 'yy']:
        log('item = %s', item)

    log('--- tuple unpacking')

    # Note: tuple_iter_1 and tuple_iter_2 are also top-level locals, and are
    # rooted at the top level.
    # They could be SCOPED.
    list_of_tuples = [(5, 'five'), (6, 'six')]
    for tuple_iter_1, tuple_iter_2 in list_of_tuples:
        log("- [%d] %s", tuple_iter_1, tuple_iter_2)

    log('--- one arg xrange()')

    m = 2
    n = 3

    for j in xrange(m * 2):
        log("%d", j)

    log('--- two arg xrange()')

    # TODO: reuse index variable j
    for k in xrange(m + 2, n + 5):
        log("%d", k)

    log('--- three arg xrange()')

    # should iterate exactly once
    for m in xrange(0, 5, 2):
        log("%d", m)

    log('--- three arg reverse xrange()')

    # should iterate exactly once
    for m in xrange(0, -1, -1):
        log("reverse %d", m)

    log('--- enumerate()')

    for i, c in enumerate(CATS):
        log('%d %s', i, c)

    for i, pair in enumerate(list_of_tuples):
        index, s = pair
        log('%d %d %s', i, index, s)

    # TODO: Note: might want to combine with enumerate?  But we're not using
    # that.  We can specialize it for a list.  ReverseListIter().
    log('--- reversed() list')

    list_of_strings = ['spam', 'eggs']
    for item in reversed(list_of_strings):
        log("- %s", item)

    log('--- reversed() list with tuple unpacking')
    for i, item in reversed(list_of_tuples):
        log("- [%d] %s", i, item)


def run_tests():
    # type: () -> None

    TestForLoop()

    TestListComp()

    TestDict()


def run_benchmarks():
    # type: () -> None
    n = 500000

    result = 0

    i = 0
    while i < n:
        for j in xrange(3, 10):
            result += j

        for j, c in enumerate(CATS):
            result += j
            result += len(c)

        i += 1
    log('result = %d', result)
    log('Ran %d iterations of xrange/enumerate', n)


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
