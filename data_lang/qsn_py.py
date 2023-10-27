#!/usr/bin/env python2
"""
qsn_py.py: Python implementation of QSN that can't be translated to C++

For testing in qsn_test.py
"""

import re

QSN_LEX = re.compile(r'''
  ( \\ [nrt0'"\\]                  ) # " accepted here but not encoded
| ( \\ [xX]    [0-9a-fA-F]{2}      )
| ( \\ [uU] \{ [0-9a-fA-F]{1,6} \} ) # 21 bits fits in 6 hex digits
| ( [^'\\\t\n\0]+                  ) # literal chars; no newlines, tab, NUL
| ( '                              ) # closing quote
| ( .                              ) # invalid escape \a, trailing backslash
                                     # newline or tab
''', re.VERBOSE | re.DOTALL)  # . matches newline, a syntax error


def _CodePointToChar(code_point):
    # type: (int) -> unicode
    """
    Workaround: unichr() is limited to 0x10000 in "narrow Python builds"
    # https://stackoverflow.com/questions/7105874/valueerror-unichr-arg-not-in-range0x10000-narrow-python-build 
    """
    import struct
    return struct.pack('i', code_point).decode('utf-32')


def py_decode(s):
    # type: (str) -> str
    """Given a QSN literal in a string, return the corresponding byte
    string.

    This is basically a proof of concept of the single regex
    above.  It throws away data after the closing quote of the
    QSN string.
    """
    pos = 0
    n = len(s)

    # TODO: This should be factored into maybe_decode
    #assert s.startswith("'"), s

    need_quote = False
    if s.startswith("'"):
        need_quote = True
        pos += 1

    parts = []
    while pos < n:
        m = QSN_LEX.match(s, pos)
        assert m, s[pos:]
        #print(m.groups())

        pos = m.end(0)

        if m.group(1):
            c = m.group(0)[1]
            if c == 'n':
                part = '\n'
            elif c == 'r':
                part = '\r'
            elif c == 't':
                part = '\t'
            elif c == '0':
                part = '\0'
            elif c == "'":
                part = "'"
            elif c == '"':  # note: " not encoded, but decoded
                part = '"'
            elif c == '\\':
                part = '\\'
            else:
                raise AssertionError(m.group(0))

        elif m.group(2):
            hex_str = m.group(2)[2:]
            part = chr(int(hex_str, 16))

        elif m.group(3):
            hex_str = m.group(3)[3:-1]  # \u{ }

            code_point = int(hex_str, 16)

            ch = _CodePointToChar(code_point)
            #print('ch %r' % ch)
            part = ch.encode('utf-8')

        elif m.group(4):
            part = m.group(4)

        elif m.group(5):
            need_quote = False
            break  # closing quote

        elif m.group(6):
            raise RuntimeError('Invalid syntax %r' % m.group(6))

        parts.append(part)

    if need_quote:
        raise RuntimeError('Missing closing quote')

    return ''.join(parts)
