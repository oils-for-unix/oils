"""num.py - math functions"""
from __future__ import print_function


def Exponent(x, y):
    # type: (int, int) -> int
    result = 1
    for i in xrange(y):
        result *= x
    return result
