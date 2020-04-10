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

Oil usgae:

  maybe_shell_encode() can be used in 5 places:
  Everywhere string_ops.ShellQuoteOneLin is used.

  - argv[i] for xtrace:
  - set
  - declare -p
  - printf %q
  - ${var@Q}

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
"""
from __future__ import print_function

import re


def maybe_shell_encode(s, bit8_display='p'):
  """Encode simple strings to a "bare" word, and complex ones to a QSN literal.

  Shell strings sometimes need the $'' prefix, e.g. for $'\x00'.

  This technically isn't part of QSN, but shell can understand QSN, as long as
  it doesn't have \u{}, e.g. bit8_display != 'u'.
  """

  quote = 0  # no quotes

  if len(s) == 0:  # empty string DOES need quotes!
    quote = 1
  else:
    for ch in s:
      # [a-zA-Z0-9._-\_] are filename chars and don't need quotes
      if (ch in '.-_' or
          'a' < ch and ch < 'z' or
          'A' < ch and ch < 'Z' or
          '0' < ch and ch < '9'):
        continue  # quote is still 0

      quote = 1

      if (ch in '\\\'\r\n\t\0' or
          ch < ' ' or
          ch > '\x7F'):
        # It needs quotes like $''
        quote = 2  # max quote, so don't look at the rest of the string
        break

  # should we also figure out the length?
  parts = []

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


def maybe_encode(s, bit8_display='p'):
  """Encode simple strings to a "bare" word, and complex ones to a QSN literal.
  """
  quote = 0

  if len(s) == 0:
    quote = 1
  else:
    for ch in s:
      # [a-zA-Z0-9._-\_] are filename chars and don't need quotes
      if (ch in '.-_' or
          'a' < ch and ch < 'z' or
          'A' < ch and ch < 'Z' or
          '0' < ch and ch < '9'):
        continue  # quote is still 0

      quote = 1

  parts = []

  if quote:
    parts.append("'")
    _encode_bytes(s, bit8_display, parts)
    parts.append("'")
  else:
    return s

  return ''.join(parts)


def encode(s, bit8_display='p'):
  parts = []
  parts.append("'")
  _encode_bytes(s, bit8_display, parts)
  parts.append("'")
  return ''.join(parts)


def _encode_bytes(s, bit8_display, parts):
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

    elif ch < ' ':
      part = '\\x%02x' % ord(ch)

    elif ch >= '\x7f':
      if bit8_display == 'x':
        # TODO: Print this LITERALLY if
        # unicode=DO_NOT_TOUCH
        # unicode=ESCAPE : gives you \x
        # unicode=DECODE : gives you \u
        #
        # unicode='x' unicode='u' unicode=''  default
        # or maybe:
        # high_bit='u' high_bit='x'  high_bit=p : pass through

        part = '\\x%02x' % ord(ch)
      elif bit8_display == 'u':
        # need utf-8 decoder
        raise NotImplementedError()
      else:
        part = ch

    else:  # a literal  character
      part = ch

    parts.append(part)


QSN_LEX = re.compile(r'''
  ( \\ [nrt0'"\\]                  ) # " accepted here but not encoded
| ( \\ [xX]    [0-9a-fA-F]{2}      )
| ( \\ [uU] \{ [0-9a-fA-F]{1,6} \} ) # 21 bits fits in 6 hex digits
| ( [^'\\]+                        ) # regular chars
| ( '                              ) # closing quote
| ( .                              ) # invalid escape \a, or trailing backslash
''', re.VERBOSE)


def decode(s):
  """Given a QSN literal in a string, return the corresponding byte string."""

  pos = 0
  n = len(s)

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
  """

  Logic:

  If we're looking at ', then call decode().

  Otherwise return until the next space/tab/newline or ' or \?
  \ can only appear within quotes.

  abc
  """
  pass
