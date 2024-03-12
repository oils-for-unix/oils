#!/usr/bin/env python2
"""
test_cast.py 
"""
from __future__ import print_function

import os
from typing import Tuple, cast

from mycpp import mylib
from mycpp.mylib import log, tagswitch


class ColorOutput(object):
    """Abstract base class for plain text, ANSI color, and HTML color."""

    def __init__(self, f):
        # type: (mylib.Writer) -> None
        self.f = f
        self.num_chars = 0

    def WriteRaw(self, raw):
        # type: (Tuple[str, int]) -> None
        """
        Write raw data without escaping, and without counting control codes in the
        length.
        """
        s, num_chars = raw
        self.f.write(s)
        self.num_chars += num_chars

    def GetRaw(self):
        # type: () -> Tuple[str, int]

        # NOTE: Ensured by NewTempBuffer()
        f = cast(mylib.BufWriter, self.f)
        return f.getvalue(), self.num_chars


def TestCastBufWriter():
    # type: () -> None
    """For debugging a problem with StackRoots generation"""

    f = mylib.BufWriter()
    out = ColorOutput(f)
    out.WriteRaw(('yo', 2))
    s, num_chars = out.GetRaw()
    print(s)


class value_t:

    def __init__(self):
        # type: () -> None
        pass

    def tag(self):
        # type: () -> int
        raise NotImplementedError()


class value__Int(value_t):

    def __init__(self, i):
        # type: (int) -> None
        self.i = i

    def tag(self):
        # type: () -> int
        return 1


class value__Eggex(value_t):

    def __init__(self, ere):
        # type: (str) -> None
        self.ere = ere

    def tag(self):
        # type: () -> int
        return 2


def TestSwitchDowncast(val):
    # type: (value_t) -> None
    """
    The common val -> UP_val -> val pattern
    """
    UP_val = val
    with tagswitch(val) as case:
        if case(1):
            val = cast(value__Int, UP_val)
            print('Int = %d' % val.i)
        elif case(2):
            val = cast(value__Eggex, UP_val)
            print('Eggex = %r' % val.ere)
        else:
            print('other')


def TestSwitchDowncastBad(val):
    # type: (value_t) -> None
    """
    TODO: Could we insert the UP_val automatically?

    Possible rules:

    (1) with tagswitch(cell.val) translates to

        value_t* UP_val = cell->val;
        switch (val) {

    (2) You need MyPy casts sometimes

    unrelated = None
    with tagswitch(val) as case:
        if case(value_e.Int):
            val = cast(value.Int, val)
            print('i = %d' % val.i)

        elif case(value_e.Str):
            unrelated = cast(str, obj)
            print('String')

    (3) Then the C++ casts would look like:

    value_t* UP_val = cell->val;
    switch (val) {
        case value_e::Int {
            # How do we know to generate a NEW var here, without the UP_val
            # heuristic?
            #
            # OK well we can simply use the switch variable name?  It it
            # matches, we create a new var.
            #
            # Technical problem: it's INSIDE a block, so we have to "look
            # ahead" to the first thing in the block.

            value::Int* val = static_cast<value::Int*>(val);
        }
        case value_e::Str {
            // NOT a new variable
            unrelated = static_cast<Str*>(obj);
        }
    }
    """

    #UP_val = val
    with tagswitch(val) as case:
        if case(1):
            val = cast(value__Int, val)
            print('Int')
            #print('Int = %d' % val.i)
        elif case(2):
            val = cast(value__Eggex, val)
            print('Eggex')
            # If we enable this, then it fails to compile
            #print('Eggex = %r' % val.ere)
        else:
            print('other')


def TestCastInSwitch():
    # type: () -> None

    # Inspired by HasAffix()

    e = value__Eggex('[0-9]+')

    pattern_val = e  # type: value_t

    pattern_eggex = None  # type: value__Eggex
    i = 42
    with tagswitch(pattern_val) as case:
        if case(1):  # Int
            raise AssertionError()
        elif case(2):
            pattern_eggex = cast(value__Eggex, pattern_val)
        else:
            raise AssertionError()

    print('eggex = %r' % pattern_eggex.ere)


def run_tests():
    # type: () -> None

    TestCastBufWriter()
    TestSwitchDowncast(value__Eggex('[0-9]'))
    TestSwitchDowncast(value__Int(42))

    TestSwitchDowncastBad(value__Eggex('[0-9]'))
    TestSwitchDowncastBad(value__Int(42))

    TestCastInSwitch()


def run_benchmarks():
    # type: () -> None
    raise NotImplementedError()


if __name__ == '__main__':
    if os.getenv('BENCHMARK'):
        log('Benchmarking...')
        run_benchmarks()
    else:
        run_tests()
