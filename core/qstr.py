#!/usr/bin/env python2
"""
qstr.py

Naming:
  CSTR is misleading
  QSTR is sort of taken by qt?  qsTr?
  str75
  rstr - Rust strings?

Tagline:
  QSTR Borrows From Rust to Express More Than JSON
  Rust strings with '' instead of ""
  Since \' and \" are allowed in Rust, this is OK

Comments on filename characters:

  .  and  ..  don't have to be quoted
  -  and  _   don't have to be quoted either
              but they are allowed to be
  Empty string isn't a valid filename, but we encode it as '' anyway, for
    readability
  Filenames like '+', 'a+b', ',' and 'a,b' will be quoted, although a given
  implementation could relax this.

  TSV2 needs different quoting rules?
    Numbers like 0.3 and 0.3ef would be ambiguous otherwise
    Or you could have a typed column?  No it's better to have redundancy.
    But for 'ls' you don't care
    $ ls
    0.3
    0.3af
    That is acceptable.

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

  native/qstr.c is a wrapper around
  cpp/qstr.c, which can be used in the C++ version
  well you will really need 2 wrappers.

  native/qstr.c and native/pyqstr?

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

Other related code:

repr() in stringobject.c in Python.
You have to allocate 2 + 4*n bytes.  2 more bytes for the quotes.

See repr() in mylib.cc.

You can interleave these two.
"""
from __future__ import print_function

import re


def shellstr_encode(s, decode_utf8=False):
  # and empty string DOES need quotes!

  quote = 0  # no quotes

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
    _encode(s, parts, decode_utf8)
    parts.append("'")
  else:  # 2
    parts.append("$'")
    _encode(s, parts, decode_utf8)
    parts.append("'")

  return ''.join(parts)


def qstr_encode(s, decode_utf8=False):
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
    _encode(s, parts, decode_utf8)
    parts.append("'")
  else:
    return s

  return ''.join(parts)


def _encode(s, parts, decode_utf8):
  """
  QSTR has 6 char tests, and 1 char range test

  str61 then?
  c6r1 ?

  6c7f
  32 - 127 is printable

  str127
  str6c

  Magic numbers: 6, ' ' = 32, 0x7f = 127
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

    elif ch < ' ' or ch >= '\x7f':
      part = '\\x%02x' % ord(ch)

    else:  # a literal  character
      part = ch

    parts.append(part)

# 5 conditions
# str75:
#  7 conditions to encode (without utf-8)
#  5 conditions to decode -- the first one has 6 parts
#
# q75 --  quoted string 75
# qbs75

Q = re.compile(r'''
  ( \\ [nrt0'"\\] )  # note: " accepted here
| ( \\ [xX] [0-9a-fA-F]{2} )
| ( \\ [uU] \{ [0-9a-fA-F]{1,6} \} )
| ( [^'\\]+ )
| ( ' )  # closing quote
| ( . )  # trailing backslash, or invalid backslash \a
''', re.VERBOSE)

def qstr_decode(s):
  pos = 0
  n = len(s)

  need_quote = False
  if s.startswith("'"):
    need_quote = True
    pos += 1

  parts = []
  while pos < n:
    m = Q.match(s, pos)
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



# Comments about Oil code structure

# Settings:
#
# argv[i] for xtrace:   Encode(s, prefix='$', must_quote=False)
# for TSV2:             Encode(s, must_quote=False)  # maybe: decode_utf8=True

# string_ops.ShellQuoteOneLine.
#   Oh actually this outputs $.  But it's not exhaustive.
#
#   And 'set'    -- buggy
#
# ShellQuote:
#   Used to print declare.  Consistent with set.
#   @Q -- this could be one line?
#
#   Used for printf %q format -- well this needs to be compatible with other hsells.
#
# qstr_encode(s)
# qstr_encode(s)

# to_qstr(s)
# from_qstr(s)
#
# pass s => to_qstr() => var q
# pass q => from_qstr() => var s

# Summary:
#   builtin_pure Set and builtin_assign declare just need to eval, so use
#    ShellQuoteOneLine
#   %q and @Q use $'' already, so they can also use ShellQuoteOneLine
#
# But what about POSIX shell?  I guess that ship has sailed.  coreutils already
# uses $''.
#
# For bernstein chaining on other servers, this sort of matters.
#
# You could have shopt -s posix_quote or something?


# help-bash:
# Why not make ${var@Q} the same as `printf %q' output?
#
# The difference is backslashes.  That's what we use for completion.
#
# So then we only need two methods:
#
# ShellQuoteB -- backslashes
# ShellQuoteOneLine
