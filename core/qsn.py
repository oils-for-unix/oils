#!/usr/bin/env python2
"""
qsn.py: Quoted String Notation.  See doc/qsn.md.

- Slogan: "QSN Adapts Rust's String Literal Notation Express What JSON Can't."
- Rust strings with '' instead of "". Since \' and \" are allowed in Rust, this
  is OK

Comments on filename characters:

  .  and  ..  don't have to be quoted
  -  and  _   don't have to be quoted either
              but they are allowed to be
  Empty string isn't a valid filename, but we encode it as '' anyway, for
    readability
  Filenames like '+', 'a+b', ',' and 'a,b' will be quoted, although a given
  implementation could relax this.

TODO:

  - Test suite.  Should it be bash, or Python 3?
  - Python 3 version
  - Pure C version using re2c
    - would be nice: if the test suite asserted that every code path is
      covered..
    - then we could use that same test suite on other implementations
- Would like contributions:
  - DFA-based "push" decoder
  - fun: branchless, SIMD, etc.

Code Structure:

  native/qsn.c is a wrapper around
  cpp/qsn.c, which can be used in the C++ version
  well you will really need 2 wrappers.

  native/qsn.c and native/pyqsn?

UTF-8 Comments:

  The shell quoter doesn't really need to decode utf-8.  No other shell does.
  And filenames could be in some other encoding where \' for certain bytes
  looks funny, etc.

  It would be nice to have the option of UTF-8 decoding in QSTR encoder, so
  that the absence of \\x means it's well-formed UTF-8.

  We could use this code:

  https://bjoern.hoehrmann.de/utf-8/decoder/dfa/

  It returns 0, 1, or some other positive number if more bytes have to be read.

  So if it returns REJECT, then back up to the previous valid position.

  And print the rest of the string byte-by-byte in the \xff style.

Related code:
  repr() in stringobject.c in Python.  Copied to repr() in mylib.cc.
  You have to allocate 2 + 4*n bytes.  2 more bytes for the quotes.

Oil usage:

  maybe_shell_encode() can be used in 5 places:
  Everywhere string_ops.ShellQuoteOneLin is used.

  - to display argv[i]
    - set -x / xtrace
    - 'jobs' list
    - 'getopts' error message
  - to display variable values
    - 'set'
    - declare -p
  - user functions
    - printf %q
    - ${var@Q} (not done yet)

  Other:

  - for QTSV:  maybe_tsv_encode()

We still need:

  ShellQuoteB - backslash shell quoting, e.g. for spaces.  Not technically
  related to QSN.

Oil User API:

  pass s => to_qsn() => var q
  pass q => from_qsn() => var s

  to-qsn $s :q
  from-qsn $q :orig
  test $s = $orig; echo $?

help-bash thread:
  Why not make ${var@Q} the same as 'printf %q' output?
  It was an accident.

Embedding within JSON strings:

  "'\\x00\\''"

Can be shortened to:

  "\\x00\\'"

In other words, we don't need the leading and trailing quotes.  Note that
backslashes are doubled.
"""
from __future__ import print_function

from mycpp import mylib

from typing import List


BIT8_RAW = 0  # Pass through.  The default now, but bash and other shells
              # do better.  They know that '\xce\xce\xbc' is an invalid byte to
              # be escaped, then UTF-8.
BIT8_X = 1  # escape everything as \xff
BIT8_U = 2  # decode and escape as \u03bc.  Not implemented yet.
            # Note: should we do error recovery?  Other shells do.
MUST_QUOTE = 4


# Functions that aren't translated.  We don't define < and > on strings, and it
# can be done more simply with character tests.

if mylib.PYTHON:
  def IsUnprintableLow(ch):
    # type: (str) -> bool
    return ch < ' '

  def IsUnprintableHigh(ch):
    # type: (str) -> bool
    return ch >= '\x7f'  # 0x7f is DEL, 0x7E is ~

  def IsPlainChar(ch):
    # type: (str) -> bool
    return (ch in '.-_' or
        'a' <= ch and ch <= 'z' or
        'A' <= ch and ch <= 'Z' or
        '0' <= ch and ch <= '9')

  # mycpp can't translate this format string
  def XEscape(ch):
    # type: (str) -> str
    return '\\x%02x' % ord(ch)


def maybe_shell_encode(s, flags=0):
  # type: (str, int) -> str
  """Encode simple strings to a "bare" word, and complex ones to a QSN literal.

  Shell strings sometimes need the $'' prefix, e.g. for $'\x00'.

  This technically isn't part of QSN, but shell can understand QSN, as long as
  it doesn't have \u{}, e.g. bit8_display != BIT8_U.

  Used for:
  - xtrace showing argv
  - error message showing getopts argv
  - displaying argv array in 'jobs'

  TODO: others
  """
  quote = 0  # no quotes

  must_quote = flags & 0b100

  # last 2 bits
  bit8_display = flags & 0b11

  if len(s) == 0:  # empty string DOES need quotes!
    quote = 1
  else:
    for ch in s:
      # [a-zA-Z0-9._\-] are filename chars and don't need quotes
      if not must_quote and IsPlainChar(ch):
        continue  # quote is still 0

      quote = 1

      if ch in '\\\'\r\n\t\0' or IsUnprintableLow(ch):
        # It needs quotes like $''
        quote = 2  # max quote, so don't look at the rest of the string
        break

      # Raw strings can use '', but \xff and \u{03bc} escapes require $''.
      if IsUnprintableHigh(ch) and bit8_display != BIT8_RAW:
        quote = 2
        break

  # should we also figure out the length?
  parts = []  # type: List[str]

  if quote == 0:
    return s
  elif quote == 1:
    parts.append("'")
    _encode_bytes(s, bit8_display, parts)
    parts.append("'")
  else:  # 2
    parts.append("$'")
    _encode_bytes(s, bit8_display, parts)
    parts.append("'")

  return ''.join(parts)


def maybe_encode(s, bit8_display=BIT8_RAW):
  # type: (str, int) -> str
  """Encode simple strings to a "bare" word, and complex ones to a QSN literal.

  Used for: ASDL pretty printing.  There, we don't care about the validity of
  shell strings.
  """
  quote = 0

  if len(s) == 0:
    quote = 1
  else:
    for ch in s:
      # [a-zA-Z0-9._-\_] are filename chars and don't need quotes
      if IsPlainChar(ch):
        continue  # quote is still 0

      quote = 1

  if not quote:
    return s

  parts = []  # type: List[str]
  parts.append("'")
  _encode_bytes(s, bit8_display, parts)
  parts.append("'")
  return ''.join(parts)


def encode(s, bit8_display=BIT8_RAW):
  # type: (str, int) -> str
  parts = []  # type: List[str]
  parts.append("'")
  _encode_bytes(s, bit8_display, parts)
  parts.append("'")
  return ''.join(parts)


def _encode_bytes(s, bit8_display, parts):
  # type: (str, int, List[str]) -> None
  """The core encoding routine.

  Used by encode(), maybe_encode(), and maybe_shell_encode().
  """
  for ch in s:
    # append to buffer
    if ch == '\\':
      part = r'\\'
    elif ch == "'":
      part = "\\'"
    elif ch == '\n':
      part = '\\n'
    elif ch == '\r':
      part = '\\r'
    elif ch == '\t':
      part = '\\t'
    elif ch == '\0':
      part = '\\0'

    elif IsUnprintableLow(ch):
      part = XEscape(ch)

    elif IsUnprintableHigh(ch):
      if bit8_display == BIT8_X:
        part = XEscape(ch)
      elif bit8_display == BIT8_U:
        # need utf-8 decoder
        raise NotImplementedError()
      else:
        part = ch

    else:  # a literal  character
      part = ch

    parts.append(part)


# TODO: Translate this to something that can be built into the OVM tarball.

if mylib.PYTHON:  # So we don't translate it
  # Hack so so 'import re' isn't executed, but unit tests still work
  import sys
  #print(sorted(sys.modules))
  if 'unittest' in sys.modules:
    import re
    QSN_LEX = re.compile(r'''
      ( \\ [nrt0'"\\]                  ) # " accepted here but not encoded
    | ( \\ [xX]    [0-9a-fA-F]{2}      )
    | ( \\ [uU] \{ [0-9a-fA-F]{1,6} \} ) # 21 bits fits in 6 hex digits
    | ( [^'\\]+                        ) # regular chars
    | ( '                              ) # closing quote
    | ( .                              ) # invalid escape \a, or trailing backslash
    ''', re.VERBOSE)

    def decode(s):
      # type: (str) -> str
      """Given a QSN literal in a string, return the corresponding byte string."""

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
          part = unichr(int(hex_str, 16)).encode('utf-8')

        elif m.group(4):
          part = m.group(4)

        elif m.group(5):
          need_quote = False
          continue  # no part to append

        elif m.group(6):
          raise RuntimeError('Invalid syntax %r' % m.group(6))

        parts.append(part)

      if need_quote:
        raise RuntimeError('Missing closing quote')

      return ''.join(parts)


#
# QTSV -- A Safe, Unix-y Interchange Format For Tables
#
# - Why?  Because CSV and TSV records can span records.
# - Because data frames need to be transported between Pandas and R without
#   using types.
#

def maybe_tsv_encode(s, bit8_display):
  # type: (str, int) -> str
  """
  TSV2 needs different quoting rules?

    Numbers like 0.3 and 0.3ef would be ambiguous otherwise
    Or you could have a typed column?  No it's better to have redundancy.
    But for 'ls' you don't care
    $ ls
    0.3
    0.3af
    That is acceptable.

  """
  pass


def tsv_decode(s):
  # type: (str) -> str
  """
  Logic:

  If we're looking at ', then call decode().

  Otherwise return until the next space/tab/newline or ' or \?
  \ can only appear within quotes.

  abc
  """
  pass
