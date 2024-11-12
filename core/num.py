"""num.py - math functions"""
from __future__ import print_function

from _devbuild.gen.value_asdl import value
from mycpp import mops


def ToBig(i):
    # type: (int) -> value.Int
    return value.Int(mops.IntWiden(i))


def Exponent(x, y):
    # type: (mops.BigInt, mops.BigInt) -> mops.BigInt

    # TODO: can we avoid this?
    y_int = mops.BigTruncate(y)

    assert y_int >= 0, 'checked by caller'

    result = mops.BigInt(1)
    for i in xrange(y_int):
        result = mops.Mul(result, x)
    return result
