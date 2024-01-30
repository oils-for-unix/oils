Data Languages
==============

This directory has implementations of data languages that can and should be
reimplemented outside Oils.

## J8 Notation

See `doc/j8-notation.md` for details.

Pure C code, which can be used by CPython and Oils C++:

    j8.h

Shared test code:

    j8_test_lib.{h,c}

C library used by CPython, using `malloc() realloc()`:

    j8_libc.{h,c}  j8_libc_test.c

Parser and printer in Python, translated by mycpp:

    j8.py
    pyj8.py     # function that can be optimized in C++
    j8_lite.py  # string-only functions, used by ASDL runtime
                # so it must have few dependencies

## UTF-8

Tests for different implementations:

    utf8_test.cc

## Packle

TODO
