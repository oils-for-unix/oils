#!/usr/bin/env python2
"""
j8_str.py
"""

from mycpp import mylib

def Encode(s, mode, buf):
    # type: (str, int, mylib.BufWriter) -> int
    """
    Callers:

    - json write
    - j8 write
    - the = operator
    - 'declare' prints in bash compatible syntax

    Algorithm:

    1. Decode UTF-8 rune-by-rune, with 4 cases
       - 1 byte
       - 2 bytes
       - 3 bytes - is this the surrrogate one?
       - 4 bytes

    While detecting all these errors:
       - Invalid start byte
       - Invalid continuation byte
       - Incomplete UTF-8 char
       - Over-long UTF-8 encoding
       - Decodes to invalid code point (surrogate)
         - this changed in 2003; WTF-8 allows it

    Error handling options:
       JSON mode: Either
       - errors are exceptions
       - errors become Unicode Replacement Char
       Option: unpaired surrogates like \\udc00 become errors, because errors
       shouldn't travel over the wire

       J8 mode: No errors by definition
       - All errors become \yff

    2. Encode in different modes

       JSON mode:
         Prefer literal UTF-8
         must use \\udc00 at times, so the overall message is valid UTF-8

       J8 mode:
         Prefer literal UTF-8
         All errors become \yff
         Return a flag so you know to add the j"" prefix when using these.
         Option to prefer \\u{123456}

       = mode:
         Option to prefer \\u{123456}

       Shell mode:
         Prefer literal UTF-8
         Errors can be \\xff, not \yff
         Option (low priority): use \\u1234 \\U00123456
    """
    return 0


def Decode(s, mode, buf):
    # type: (str, int, mylib.BufWriter) -> int
    """
    Should we call Parse() with 

        lex_mode_e.J8_Str
        lex_mode_e.JSON
    ?

    Callers:

    - json read
    - j8 read
    - Possibly the j"\yff" lexer, although that produces tokens first.

    The lexer for $'\x00' is different.

    1. Decode by backslash escapes \n etc.

    JSON mode: \\u1234 only
    J8 mode: \\yff and \\u{123456}

    Errors:
      Malformed escapes
    """
    return 0


def py_decode(s):
    # type: (str) -> str

    # TODO: Can use a regex as a demo
    # J8 strings are a regular language
    return s
