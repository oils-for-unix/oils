#!/usr/bin/env python
"""
libstr.py - String library functions that can be exposed with a saner syntax.

Instead of

local y=${x//a*/b}

var y = x -> sub('a*', 'b', :ALL)

Or maybe:

var y = x -> sub( g/a*/, 'b', :ALL)
"""

import libc

from osh.meta import Id
from core import glob_
from core import util

log = util.log
e_die = util.e_die


def Utf8Encode(code):
  """Return utf-8 encoded bytes from a unicode code point.

  Based on https://stackoverflow.com/a/23502707
  """
  num_cont_bytes = 0

  if code <= 0x7F:
    return chr(code & 0x7F)  # ASCII

  elif code <= 0x7FF:
    num_cont_bytes = 1
  elif code <= 0xFFFF:
    num_cont_bytes = 2
  elif code <= 0x10FFFF:
    num_cont_bytes = 3

  else:
    return '\xEF\xBF\xBD'  # unicode replacement character

  bytes_ = []
  for _ in xrange(num_cont_bytes):
    bytes_.append(0x80 | (code & 0x3F))
    code >>= 6

  b = (0x1E << (6-num_cont_bytes)) | (code & (0x3F >> num_cont_bytes))
  bytes_.append(b)
  bytes_.reverse()

  # mod 256 because Python ints don't wrap around!
  return ''.join(chr(b & 0xFF) for b in bytes_)


# TODO: Add details of the invalid character/byte here?

INCOMPLETE_CHAR = 'Incomplete UTF-8 character'
INVALID_CONT = 'Invalid UTF-8 continuation byte'
INVALID_START = 'Invalid start of UTF-8 character'


def _CheckContinuationByte(byte):
  if (ord(byte) >> 6) != 0b10:
    raise util.InvalidUtf8(INVALID_CONT)


def _NextUtf8Char(s, i):
  """
  Given a string and a byte offset, returns the byte position of the next char.
  Validates UTF-8.
  """
  byte_as_int = ord(s[i])  # Should never raise IndexError

  try:
    if (byte_as_int >> 7) == 0b0:
      i += 1
    elif (byte_as_int >> 5) == 0b110:
      _CheckContinuationByte(s[i+1])
      i += 2
    elif (byte_as_int >> 4) == 0b1110:
      _CheckContinuationByte(s[i+1])
      _CheckContinuationByte(s[i+2])
      i += 3
    elif (byte_as_int >> 3) == 0b11110:
      _CheckContinuationByte(s[i+1])
      _CheckContinuationByte(s[i+2])
      _CheckContinuationByte(s[i+3])
      i += 4
    else:
      raise util.InvalidUtf8(INVALID_START)
  except IndexError:
    raise util.InvalidUtf8(INCOMPLETE_CHAR)

  return i


def CountUtf8Chars(s):
  """Returns the number of utf-8 characters in the byte string 's'.

  TODO: Raise exception rather than returning a string, so we can set the exit
  code of the command to 1 ?

  $ echo ${#bad}
  Invalid utf-8 at index 3 of string 'bad': 'ab\xffd'
  $ echo $?
  1
  """
  num_chars = 0
  num_bytes = len(s)
  i = 0
  while i < num_bytes:
    i = _NextUtf8Char(s, i)
    num_chars += 1
  return num_chars


def AdvanceUtf8Chars(s, num_chars, byte_offset):
  """
  Advance a certain number of UTF-8 chars, beginning with the given byte
  offset.  Returns a byte offset.

  If we got past the end of the string
  """
  num_bytes = len(s)
  i = byte_offset  # current byte position

  for _ in xrange(num_chars):
    # Neither bash or zsh checks out of bounds for slicing.  Either begin or
    # length.
    if i >= num_bytes:
      return i
      #raise RuntimeError('Out of bounds')

    i = _NextUtf8Char(s, i)

  return i


# Implementation without Python regex:
#
# (1) PatSub: I think we fill in GlobToExtendedRegex, then use regcomp and
# regexec.  in a loop.  fnmatch() does NOT given positions of matches.
#
# (2) Strip -- % %% # ## -
#
# a. Fast path for constant strings.
# b. Convert to POSIX extended regex, to see if it matches at ALL.  If it
# doesn't match, short circuit out?  We can't do this with fnmatch.
# c. If it does match, call fnmatch() iteratively over prefixes / suffixes.
#
# - # shortest prefix - [:1], [:2], [:3] until it matches
# - ## longest prefix - [:-1] [:-2], [:3].  Works because fnmatch does not
#                       match prefixes, it matches EXATLY.
# - % shortest suffix - [-1:] [-2:] [-3:] ...
# - %% longest suffix - [1:] [2:] [3:]
#
# See remove_pattern() in subst.c for bash, and trimsub() in eval.c for
# mksh.  Dash doesn't implement it.


# TODO:
# - Unicode support: Convert both pattern, string, and replacement to unicode,
#   then the result back at the end.
# - Add location info to errors.  Maybe pass spid pair all the way down.
#   - Compile time errors for [[:space:]] ?

def DoUnarySuffixOp(s, op, arg):
  """Helper for ${x#prefix} and family."""

  # Fast path for constant strings.
  if not glob_.LooksLikeGlob(arg):
    if op.op_id in (Id.VOp1_Pound, Id.VOp1_DPound):  # const prefix
      if s.startswith(arg):
        return s[len(arg):]
      else:
        return s

    elif op.op_id in (Id.VOp1_Percent, Id.VOp1_DPercent):  # const suffix
      if s.endswith(arg):
        # Mutate it so we preserve the flags.
        return s[:-len(arg)]
      else:
        return s

    else:  # e.g. ^ ^^ , ,,
      raise AssertionError(op.op_id)

  # For patterns, do fnmatch() in a loop.
  #
  # TODO: Check another fast path first?
  #
  # v=aabbccdd
  # echo ${v#*b}  # strip shortest prefix
  #
  # If the whole thing doesn't match '*b*', then no test can succeed.  So we
  # can fail early.  Conversely echo ${v%%c*} and '*c*'.

  n = len(s)
  if op.op_id == Id.VOp1_Pound:  # shortest prefix
    # 'abcd': match 'a', 'ab', 'abc', ...
    for i in xrange(1, n+1):
      #log('Matching pattern %r with %r', arg, s[:i])
      if libc.fnmatch(arg, s[:i]):
        return s[i:]
    else:
      return s

  elif op.op_id == Id.VOp1_DPound:  # longest prefix
    # 'abcd': match 'abc', 'ab', 'a'
    for i in xrange(n, 0, -1):
      #log('Matching pattern %r with %r', arg, s[:i])
      if libc.fnmatch(arg, s[:i]):
        return s[i:]
    else:
      return s

  elif op.op_id == Id.VOp1_Percent:  # shortest suffix
    # 'abcd': match 'abc', 'ab', 'a'
    for i in xrange(n-1, -1, -1):
      #log('Matching pattern %r with %r', arg, s[:i])
      if libc.fnmatch(arg, s[i:]):
        return s[:i]
    else:
      return s

  elif op.op_id == Id.VOp1_DPercent:  # longest suffix
    # 'abcd': match 'abc', 'bc', 'c', ...
    for i in xrange(0, n):
      #log('Matching pattern %r with %r', arg, s[:i])
      if libc.fnmatch(arg, s[i:]):
        return s[:i]
    else:
      return s


def _AllMatchPositions(s, regex):
  """Returns a list of all (start, end) match positions of the regex against s.

  (If there are no matches, it returns the empty list.)
  """
  matches = []
  pos = 0
  while True:
    m = libc.regex_first_group_match(regex, s, pos)
    if m is None:
      break
    matches.append(m)
    start, end = m
    #log('m = %r, %r' % (start, end))
    pos = end  # advance position
  return matches


def _PatSubAll(s, regex, replace_str):
  parts = []
  prev_end = 0
  for start, end in _AllMatchPositions(s, regex):
    parts.append(s[prev_end:start])
    parts.append(replace_str)
    prev_end = end
  parts.append(s[prev_end:])
  return ''.join(parts)


class _Replacer(object):
  def Replace(self, s, op):
    raise NotImplementedError


class _ConstStringReplacer(_Replacer):
  def __init__(self, pat, replace_str):
    self.pat = pat
    self.pat_len = len(pat)
    self.replace_str = replace_str

  def Replace(self, s, op):
    if op.do_all:
      return s.replace(self.pat, self.replace_str)
    elif op.do_prefix:
      if s.startswith(self.pat):
        return self.replace_str + s[self.pat_len:]
      else:
        return s
    elif op.do_suffix:
      if s.endswith(self.pat):
        # NOTE: This handles ${s/#/foo}.  See spec test in var-op-strip.
        i = len(s) - self.pat_len
        return s[:i] + self.replace_str
      else:
        return s
    else:
      return s.replace(self.pat, self.replace_str, 1)  # just the first one


class _GlobReplacer(_Replacer):
  def __init__(self, regex, replace_str):
    # TODO: It would be nice to cache the compilation of the regex here,
    # instead of just the string.  That would require more sophisticated use of
    # the Python/C API in libc.c, which we might want to avoid.
    self.regex = regex
    self.replace_str = replace_str

  def Replace(self, s, op):
    regex = '(%s)' % self.regex  # make it a group

    if op.do_all:
      return _PatSubAll(s, regex, self.replace_str)  # loop over matches

    if op.do_prefix:
      regex = '^' + regex
    elif op.do_suffix:
      regex = regex + '$'

    m = libc.regex_first_group_match(regex, s, 0)
    #log('regex = %r, s = %r, match = %r', regex, s, m)
    if m is None:
      return s
    start, end = m
    return s[:start] + self.replace_str + s[end:]


def MakeReplacer(pat, replace_str):
  """Helper for ${x/pat/replace}

  Parses 'pat' and returns either a _GlobReplacer or a _ConstStringReplacer.

  Using these objects is more efficient when performing the same operation on
  multiple strings.
  """
  regex, warnings = glob_.GlobToERE(pat)
  if warnings:
    # TODO: Add strict mode and expose warnings.
    pass
  if regex is None:
    return _ConstStringReplacer(pat, replace_str)
  else:
    return _GlobReplacer(regex, replace_str)
