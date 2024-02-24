"""
Math operations, e.g. for arbitrary precision integers 

They are currently int64_t, rather than C int, but we want to upgrade to
heap-allocated integers.

Regular int ops can use the normal operators + - * /, or maybe i_add() if we
really want.  Does that make code gen harder or worse?

I suppose float ops could be + - * / too, but it feels nicer to develop a
formal interface?
"""
from __future__ import print_function

from typing import cast


class BigInt(int):
    """In Python, all integers are big.  In C++, only some are."""
    pass


def ToStr(b):
    # type: (BigInt) -> str
    return str(b)


def ToBigInt(s, base=10):
    # type: (str, int) -> BigInt
    return BigInt(s, base)  # like int(s, base)


def BigTruncate(b):
    # type: (BigInt) -> int
    """Only truncates in C++"""
    return cast(int, b)


def IntWiden(b):
    # type: (int) -> BigInt
    """Only widens in C++"""
    return cast(BigInt, b)


def FromBool(b):
    # type: (bool) -> BigInt
    """Only widens in C++"""
    return BigInt(1) if b else BigInt(0)


# Can't use operator overloading


def Add(a, b):
    # type: (BigInt, BigInt) -> BigInt
    return cast(BigInt, a + b)


def Sub(a, b):
    # type: (BigInt, BigInt) -> BigInt
    return cast(BigInt, a - b)


def Mul(a, b):
    # type: (BigInt, BigInt) -> BigInt
    return cast(BigInt, a * b)


def Div(a, b):
    # type: (BigInt, BigInt) -> BigInt
    """
    Divide, for positive integers only

    Question: does Oils behave like C remainder when it's positive?  Then we
    could be more efficient with a different layering?
    """
    assert a >= 0 and b >= 0, (a, b)
    return cast(BigInt, a // b)


def Rem(a, b):
    # type: (BigInt, BigInt) -> BigInt
    """
    Remainder, for positive integers only
    """
    assert a >= 0 and b >= 0, (a, b)
    return cast(BigInt, a % b)


def Equal(a, b):
    # type: (BigInt, BigInt) -> bool
    return a == b


def Greater(a, b):
    # type: (BigInt, BigInt) -> bool
    return a > b


# GreaterEq, Less, LessEq can all be expressed as the 2 ops above


def LShift(a, b):
    # type: (BigInt, BigInt) -> BigInt
    """
    Any semantic issues here?  Signed left shift
    """
    return cast(BigInt, a << b)


def RShift(a, b):
    # type: (BigInt, BigInt) -> BigInt
    return cast(BigInt, a >> b)


def BitAnd(a, b):
    # type: (BigInt, BigInt) -> BigInt
    return cast(BigInt, a & b)


def BitOr(a, b):
    # type: (BigInt, BigInt) -> BigInt
    return cast(BigInt, a | b)


def BitXor(a, b):
    # type: (BigInt, BigInt) -> BigInt
    return cast(BigInt, a ^ b)


def BitNot(a):
    # type: (BigInt) -> BigInt
    return cast(BigInt, ~a)
