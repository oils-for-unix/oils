#!/usr/bin/env python2
from __future__ import print_function

from mycpp import mylib
from mycpp.mylib import log

from typing import Tuple, List

_ = log

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


def _EscapeUnprintable(s, buf, j8_escape=False):
    # type: (str, mylib.BufWriter, bool) -> None
    """ Print a string literal with required escapes like \\n

    \\u001f for JSON
    \\u{1f} for J8 - these are "u6 escapes"
    """
    for ch in s:
        escaped = _COMMON_ESCAPES.get(ch)
        if escaped is not None:
            buf.write(escaped)
            continue

        if ch == "'" and j8_escape:
            buf.write(r"\'")
            continue

        if ch == '"' and not j8_escape:
            buf.write(r'\"')
            continue

        char_code = ord(ch)
        if char_code < 0x20:  # like IsUnprintableLow
            if j8_escape:
                buf.write(r'\u{%x}' % char_code)
            else:
                buf.write(r'\u%04x' % char_code)
            continue

        buf.write(ch)


# COPY
LOSSY_JSON = 1 << 3  # JSON is lossy


def WriteString(s, options, buf):
    # type: (str, int, mylib.BufWriter) -> int
    """ Encode a string in J8 format

    Does UTF-8 decoding.  TODO: replace this with C version, because Python 2
    s.decode('utf-8') allows invalid surrogates.

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
    """
    pos = 0
    portion = s
    invalid_utf8 = []  # type: List[Tuple[int, int]]
    while True:
        # Problem: Python 2 UTF-8 decoder allows bytes that correspond to
        # surrogates (but Python 3 doesn't)
        #
        # TODO:
        # - JSON behavior: round trip to "\ud83e"
        # - J8 behavior: use b'\yed\ya0\ybe'
        #
        # The Bjoern DFA will reject it, but we need the code point to be able
        # to output \ud83e.
        #
        # So we need a modified Bjoern DFA in both Python and C++, with a
        # UTF8_ACCEPT_SURROGATE state!!!  It's not ACCEPT, but you can get the
        # code point out.
        # Maybe we can visually inspect the states?

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
        if options & LOSSY_JSON:  # JSON
            buf.write('"')
            pos = 0
            for start, end in invalid_utf8:
                _EscapeUnprintable(s[pos:start], buf)

                for i in xrange(start, end):
                    # Unicode replacement char is U+FFFD, so write encoded form
                    # >>> '\ufffd'.encode('utf-8')
                    # b'\xef\xbf\xbd'
                    buf.write('\xef\xbf\xbd')

                pos = end
                #log('pos %d', pos)

            # Last part
            _EscapeUnprintable(s[pos:], buf)
            buf.write('"')

        else:
            buf.write("b'")
            pos = 0
            for start, end in invalid_utf8:
                _EscapeUnprintable(s[pos:start], buf, j8_escape=True)

                for i in xrange(start, end):
                    buf.write('\y%x' % ord(s[i]))

                pos = end
                #log('pos %d', pos)

            # Last part
            _EscapeUnprintable(s[pos:], buf, j8_escape=True)
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
    """ Used for J8 decoding """
    part = s[start:end]
    try:
        part.decode('utf-8')
    except UnicodeDecodeError as e:
        return False
    return True


# vim: sw=4
