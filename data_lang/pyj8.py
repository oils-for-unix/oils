#!/usr/bin/env python2
from __future__ import print_function

from mycpp import mylib
from mycpp.mylib import log

from typing import Tuple, List

_ = log


def WriteInt(i, buf):
    # type: (int, mylib.BufWriter) -> None
    """ C++ version can avoid allocation """
    buf.write(str(i))


def WriteFloat(f, buf):
    # type: (float, mylib.BufWriter) -> None
    """ C++ version can avoid allocation """
    buf.write(str(f))


def EncodeString(s, options):
    # type: (str, int) -> str
    buf = mylib.BufWriter()
    WriteString(s, options, buf)
    return buf.getvalue()


# similar to frontend/consts.py
_COMMON_ESCAPES = {
    # Notes:
    # - we don't escape \/
    # - \' and \" are decided dynamically, based on the quote
    '\\': '\\\\',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\\n',
    '\r': '\\r',
    '\t': '\\t',
}


def _EscapeUnprintable(s, buf, is_j8=False):
    # type: (str, mylib.BufWriter, bool) -> None
    """ Print a string literal with required esceapes like \\n

    \\u001f for JSON
    \\u{1f} for J8 - these are "u6 escapes"
    """
    for ch in s:
        escaped = _COMMON_ESCAPES.get(ch)
        if escaped is not None:
            buf.write(escaped)
            continue

        if ch == "'" and is_j8:
            buf.write(r"\'")
            continue

        if ch == '"' and not is_j8:
            buf.write(r'\"')
            continue

        char_code = ord(ch)
        if char_code < 0x20:  # like IsUnprintableLow
            if is_j8:
                buf.write(r'\u{%x}' % char_code)
            else:
                buf.write(r'\u%04x' % char_code)
            continue

        buf.write(ch)


def WriteString(s, options, buf):
    # type: (str, int, mylib.BufWriter) -> int
    """
    Callers:

    - json write
    - j8 write
    - the = operator
    - pp line (x)
    - 'declare' prints in bash compatible syntax

    Simple algorithm:

    1. Decode UTF-8 
       In Python, use built-in s.decode('utf-8')
       In C++, use Bjoern DFA

    List of errors in UTF-8:
       - Invalid start byte
       - Invalid continuation byte
       - Incomplete UTF-8 char
       - Over-long UTF-8 encoding
       - Decodes to invalid code point (surrogate)
         - this changed in 2003; WTF-8 allows it

    If decoding succeeds, then surround with "" 
    - escape unprintable chars like \\u0001 and \\t \\n \\ \\"

    If decoding fails (this includes unpaired surrogates like \\udc00)
    - in J8 mode, all errors become \yff, and it must be a b'' string
    - in JSON mode, based on options, either:
      - use unicode replacement char (lossy)
      - raise an exception, so the 'json dump' fails etc.
        - Error can have location info

    LATER: Options for encoding

       JSON mode:
         Prefer literal UTF-8
         Escaping mode: must use \\udc00 at times, so the overall message is
           valid UTF-8

       J8 mode:
         Prefer literal UTF-8
         Escaping mode to use u'\\u{123456}' and perhaps b'\\u{123456}' when there
         are also errors

       = mode:
         Option to prefer \\u{123456}

    Should we generate bash-compatible strings?
       Like $'\\xff' for OSH
       Option (low priority): use \\u1234 \\U00123456
    """
    pos = 0
    portion = s
    invalid_utf8 = []  # type: List[Tuple[int, int]]
    while True:
        try:
            portion.decode('utf-8')
        except UnicodeDecodeError as e:
            invalid_utf8.append((pos + e.start, pos + e.end))
            pos += e.end
        else:
            break  # it validated
        #log('== pos %d', pos)
        portion = s[pos:]

    #print('INVALID', invalid_utf8)
    if len(invalid_utf8):
        buf.write("b'")
        pos = 0
        for start, end in invalid_utf8:
            _EscapeUnprintable(s[pos:start], buf, is_j8=True)

            for i in xrange(start, end):
                buf.write('\y%x' % ord(s[i]))

            pos = end
            #log('pos %d', pos)

        # Last part
        _EscapeUnprintable(s[pos:], buf, is_j8=True)
        buf.write("'")

    else:
        # NOTE: Our J8 encoder still emits "\u0001", not u'\u{1}'.  I guess
        # this is OK for now, but we might want a strict mode.
        buf.write('"')
        _EscapeUnprintable(s, buf)
        buf.write('"')

    return 0


def PartIsUtf8(s, start, end):
    # type: (str, int, int) -> bool
    part = s[start:end]
    try:
        part.decode('utf-8')
    except UnicodeDecodeError as e:
        return False
    return True


# vim: sw=4
