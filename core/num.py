"""num.py - math functions"""
from __future__ import print_function


def Exponent(x, y):
    # type: (int, int) -> int
    assert y >= 0, 'checked by caller'

    result = 1
    for i in xrange(y):
        result *= x
    return result

def IntDivide(x, y):
    # type: (int, int) -> int

    assert y != 0, 'checked by caller'

    sign = 1

    if x < 0:
        ax = -x
        sign = -1
    else:
        ax = x

    if y < 0:
        ay = -y
        sign *= -1
    else:
        ay = y

    # Only divide non-negative numbers in host language.  Python rounds toward
    # negative infinity, while C++ rounds toward zero.
    #
    # Oils rounds toward zero.
    return sign * (ax / ay)


def IntRemainder(x, y):
    # type: (int, int) -> int
    """Takes the sign of the first number."""

    assert y != 0, 'checked by caller'

    if x < 0:
        ax = -x
        sign = -1
    else:
        ax = x
        sign = 1

    if y < 0:
        ay = -y
    else:
        ay = y

    # Only use host language % on non-negative numbers.  Apply sign afteward.
    return sign * (ax % ay)
