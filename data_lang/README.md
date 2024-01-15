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

    j8c.{h,c}  j8c_test.c

Parser and printer in Python, translated by mycpp:

    j8.py


## Packle

TODO

## UTF-8

Tests for different implementations:

    utf8_test.cc

