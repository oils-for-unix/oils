#!/usr/bin/env python2
"""
integers.py
"""
from __future__ import print_function

import os
from mycpp import mops
from mycpp.mylib import log

from typing import cast


def run_tests():
    # type: () -> None

    a = 3 + 2
    print('a = %d' % a)

    # the way to write 1 << 31
    i1 = mops.LShift(mops.BigInt(1), mops.BigInt(31))
    i2 = mops.Add(i1, i1)
    i3 = mops.Add(i2, i1)

    # TODO: %d or %ld doesn't work, and won't work when it becomes arbitrary
    # size
    print('i1 = %s' % mops.ToStr(i1))
    print('i2 = %s' % mops.ToStr(i2))
    print('i3 = %s' % mops.ToStr(i3))
    print('')

    # This overflows an int64_t
    i4 = mops.LShift(mops.BigInt(1), mops.BigInt(63))
    #print('i4 = %s' % mops.ToStr(i4))

    # Max positive   (2 ^ (N-1)) - 1
    x = mops.LShift(mops.BigInt(1), mops.BigInt(62))
    y = mops.Sub(x, mops.BigInt(1))
    max_positive = mops.Add(x, y)
    print('max_positive = %s' % mops.ToStr(max_positive))

    # Max negative   -2 ^ (N-1)
    z = mops.Sub(mops.BigInt(0), x)
    max_negative = mops.Sub(z, x)
    print('max_negative = %s' % mops.ToStr(max_negative))

    # Round trip from string
    s1 = mops.ToStr(max_negative)
    print('max_negative string = %s' % s1)

    max_negative2 = mops.ToBigInt(s1)
    print('max_negative2 = %s' % mops.ToStr(max_negative2))

    if max_negative == max_negative2:
        print('round trip equal')

    big = mops.IntWiden(a)
    print('big = %s' % mops.ToStr(big))
    small = mops.BigTruncate(big)
    print('small = %d' % small)


def run_benchmarks():
    # type: () -> None
    pass


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
