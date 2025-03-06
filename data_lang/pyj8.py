#!/usr/bin/env python2
from __future__ import print_function

from mycpp import mylib
from mycpp.mylib import log

import fastfunc

_ = log

LOSSY_JSON_STRINGS = 1 << 3


def WriteString(s, options, buf):
    # type: (str, int, mylib.BufWriter) -> None
    """Write encoded J8 string to buffer.

    The C++ version is optimized to avoid the intermediate string.
    """
    j8_fallback = not (options & LOSSY_JSON_STRINGS)
    #print('j8_fallback %d' % j8_fallback)
    buf.write(fastfunc.J8EncodeString(s, j8_fallback))


PartIsUtf8 = fastfunc.PartIsUtf8

# vim: sw=4
