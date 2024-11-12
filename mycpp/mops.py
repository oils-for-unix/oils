"""
Math operations, e.g. for arbitrary precision integers 

They are currently int64_t, rather than C int, but we want to upgrade to
heap-allocated integers.

Regular int ops can use the normal operators + - * /, or maybe i_add() if we
really want.  Does that make code gen harder or worse?

Float ops could be + - * / too, but it feels nicer to develop a formal
interface?
"""
from __future__ import print_function

from typing import Tuple


class BigInt(object):

    def __init__(self, i):
        # type: (int) -> None
        self.i = i

    def __eq__(self, other):
        # type: (object) -> bool

        # Disabled check
        # Prevent possible mistakes.  Could do this with other operators
        # raise AssertionError('Use mops.Equal()')

        if not isinstance(other, BigInt):
            raise AssertionError()

        # Used for hashing
        return self.i == other.i

    def __gt__(self, other):
        # type: (object) -> bool
        raise AssertionError('Use functions in mops.py')

    def __ge__(self, other):
        # type: (object) -> bool
        raise AssertionError('Use functions in mops.py')

    def __hash__(self):
        # type: () -> int
        """For dict lookups."""
        return hash(self.i)


ZERO = BigInt(0)
ONE = BigInt(1)
MINUS_ONE = BigInt(-1)
MINUS_TWO = BigInt(-2)  # for printf


def ToStr(b):
    # type: (BigInt) -> str
    return str(b.i)


def ToOctal(b):
    # type: (BigInt) -> str
    return '%o' % b.i


def ToHexUpper(b):
    # type: (BigInt) -> str
    return '%X' % b.i


def ToHexLower(b):
    # type: (BigInt) -> str
    return '%x' % b.i


# Notes on recognizing integers:
#
# - mops.FromStr() uses StringToInt64() under the hood, which uses strtoll().
# But we DO NOT want to rely on strtoll() to define a language, .e. to reject
# user-facing strings.  We want to use something like match.LooksLikeInteger()
# This is part of our spec-driven philosophy.

# Regarding leading zeros, these are DIFFERENT:
#
# 1. trap ' 42 ' x  - unsigned, including 09, but not -1
# 2. echo $(( x )) - 0123 is octal, but no -0123 because that's separate I think
# 3. int(), j8 - 077 is decimal

# - a problem though is if we support 00, because sometimes that is OCTAL
#   - int("00") is zero
#   - match.LooksLikeInteger returns true
#
# Uses LooksLikeInteger and then FromStr()
# - YSH int()
# - printf builtin
# - YSH expression conversion

# Uses only FromStr()
# - j8 - uses its own regex though
# - ulimit
# - trap - NON-NEGATIVE only
# - arg parser

MAX_POS_INT = 2**63 - 1
MAX_NEG_INT = -(2**63)


def FromStr2(s, base=10):
    # type: (str, int) -> Tuple[bool, BigInt]
    """
    Simulate C++
    """
    try:
        big_int = BigInt(int(s, base))
    except ValueError:
        return (False, MINUS_ONE)
    else:
        # Simulate C++ overflow
        if big_int.i > MAX_POS_INT:
            return (False, MINUS_ONE)
        if big_int.i < MAX_NEG_INT:
            return (False, MINUS_ONE)

        return (True, big_int)


def BigTruncate(b):
    # type: (BigInt) -> int
    """Only truncates in C++"""
    return b.i


def IntWiden(i):
    # type: (int) -> BigInt
    """Only widens in C++"""
    return BigInt(i)


def FromC(i):
    # type: (int) -> BigInt
    """A no-op in C, for RLIM_INFINITY"""
    return BigInt(i)


def FromBool(b):
    # type: (bool) -> BigInt
    """Only widens in C++"""
    return BigInt(1) if b else BigInt(0)


def ToFloat(b):
    # type: (BigInt) -> float
    """Used by float(42) in Oils"""
    return float(b.i)


def FromFloat(f):
    # type: (float) -> Tuple[bool, BigInt]
    """Used by int(3.14) in Oils"""
    try:
        big = int(f)
    except ValueError:  # NAN
        return False, MINUS_ONE
    except OverflowError:  # INFINITY
        return False, MINUS_ONE
    return True, BigInt(big)


# Can't use operator overloading


def Negate(b):
    # type: (BigInt) -> BigInt
    return BigInt(-b.i)


def Add(a, b):
    # type: (BigInt, BigInt) -> BigInt
    return BigInt(a.i + b.i)


def Sub(a, b):
    # type: (BigInt, BigInt) -> BigInt
    return BigInt(a.i - b.i)


def Mul(a, b):
    # type: (BigInt, BigInt) -> BigInt
    return BigInt(a.i * b.i)


def Div(a, b):
    # type: (BigInt, BigInt) -> BigInt
    """Integer division.

    Oils rounds toward zero.

    Python rounds toward negative infinity, while C++ rounds toward zero.  We
    have to work around Python a bit.
    """
    assert b.i != 0, b.i  # divisor can't be zero -- caller checks

    # Only use Python // on non-negative numbers.  Apply sign afterward.
    sign = 1

    if a.i < 0:
        pa = -a.i
        sign = -1
    else:
        pa = a.i

    if b.i < 0:
        pb = -b.i
        sign = -sign
    else:
        pb = b.i

    return BigInt(sign * (pa // pb))


def Rem(a, b):
    # type: (BigInt, BigInt) -> BigInt
    """Integer remainder."""
    assert b.i != 0, b.i  # YSH divisor must be positive, but OSH can be negative

    # Only use Python % on non-negative numbers.  Apply sign afterward.
    if a.i < 0:
        pa = -a.i
        sign = -1
    else:
        pa = a.i
        sign = 1

    if b.i < 0:
        pb = -b.i
    else:
        pb = b.i

    return BigInt(sign * (pa % pb))


def Equal(a, b):
    # type: (BigInt, BigInt) -> bool
    return a.i == b.i


def Greater(a, b):
    # type: (BigInt, BigInt) -> bool
    return a.i > b.i


# GreaterEq, Less, LessEq can all be expressed as the 2 ops above


def LShift(a, b):
    # type: (BigInt, BigInt) -> BigInt
    assert b.i >= 0, b.i  # Must be checked by caller
    return BigInt(a.i << b.i)


def RShift(a, b):
    # type: (BigInt, BigInt) -> BigInt
    assert b.i >= 0, b.i  # Must be checked by caller
    return BigInt(a.i >> b.i)


def BitAnd(a, b):
    # type: (BigInt, BigInt) -> BigInt
    return BigInt(a.i & b.i)


def BitOr(a, b):
    # type: (BigInt, BigInt) -> BigInt
    return BigInt(a.i | b.i)


def BitXor(a, b):
    # type: (BigInt, BigInt) -> BigInt
    return BigInt(a.i ^ b.i)


def BitNot(a):
    # type: (BigInt) -> BigInt
    return BigInt(~a.i)
