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


def FromStr(s, base=10):
    # type: (str, int) -> BigInt
    return BigInt(int(s, base))


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
    """
    Divide, for positive integers only

    Question: does Oils behave like C remainder when it's positive?  Then we
    could be more efficient with a different layering?
    """
    assert a.i >= 0, a.i
    assert b.i > 0, b.i  # can't be zero, caller checks
    return BigInt(a.i // b.i)


def Rem(a, b):
    # type: (BigInt, BigInt) -> BigInt
    """
    Remainder, for positive integers only
    """
    assert a.i >= 0, a.i
    assert b.i > 0, b.i  # can't be zero, caller checks
    return BigInt(a.i % b.i)


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
