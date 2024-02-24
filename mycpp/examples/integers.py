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

    # the way to write 1 << 31
    i1 = mylib.ShiftLeft(mylib.BigInt(1), mylib.BigInt(31))
    i2 = mylib.Add(i1, i1)
    i3 = mylib.Add(i2, i1)

    # TODO: %d or %ld doesn't work, and won't work when it becomes arbitrary
    # size
    print('i1 = %s' % mylib.BigIntStr(i1))
    print('i2 = %s' % mylib.BigIntStr(i2))
    print('i3 = %s' % mylib.BigIntStr(i3))
    print('')

    # This overflows an int64_t
    i4 = mylib.ShiftLeft(mylib.BigInt(1), mylib.BigInt(63))
    #print('i4 = %s' % mylib.BigIntStr(i4))

    # Max positive   (2 ^ (N-1)) - 1
    x = mylib.ShiftLeft(mylib.BigInt(1), mylib.BigInt(62))
    y = mylib.Subtract(x, mylib.BigInt(1))
    max_positive = mylib.Add(x, y)
    print('max_positive = %s' % mylib.BigIntStr(max_positive))

    # Max negative   -2 ^ (N-1)
    z = mylib.Subtract(mylib.BigInt(0), x)
    max_negative = mylib.Subtract(z, x)
    print('max_negative = %s' % mylib.BigIntStr(max_negative))

    # Round trip from string
    s1 = mylib.BigIntStr(max_negative)
    print('max_negative string = %s' % s1)

    max_negative2 = mylib.ToBigInt(s1)
    print('max_negative2 = %s' % mylib.BigIntStr(max_negative2))

    if max_negative == max_negative2:
        print('round trip equal')

    big = mylib.SmallIntToBig(a)
    print('big = %s' % mylib.BigIntStr(big))
    small = mylib.BigIntToSmall(big)
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
