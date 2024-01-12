#!/usr/bin/env python2
from __future__ import print_function

from mycpp import mylib
from mycpp.mylib import log

import fastfunc

_ = log

LOSSY_JSON = 1 << 3

def WriteString(s, options, buf):
    # type: (str, int, mylib.BufWriter) -> None
    """Write encoded J8 string to buffer.

    The C++ version is optimized to avoid the intermediate string.
    """
    j8_fallback = not (options & LOSSY_JSON)
    #print('j8_fallback %d' % j8_fallback)
    buf.write(fastfunc.J8EncodeString(s, j8_fallback))


def PartIsUtf8(s, start, end):
    # type: (str, int, int) -> bool
    """Is a part of a string UTF-8?

    Used for J8 decoding.  TODO: Could also replace this with fastfunc?
    """
    part = s[start:end]
    try:
        part.decode('utf-8')
    except UnicodeDecodeError as e:
        return False
    return True


# vim: sw=4
