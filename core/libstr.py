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


INCOMPLETE = 'error: Incomplete utf-8'
INVALID_CONT = 'error: Invalid utf-8 continuation byte'
INVALID_START = 'error: Invalid start of utf-8 char'


def NumUtf8Chars(bytes):
  """Returns the number of utf-8 characters in the byte string 's'."""
  num_utf8_chars = 0

  num_bytes = len(bytes)
  i = 0
  while i < num_bytes:
    byte_as_int = ord(bytes[i])

    try:
      if (byte_as_int >> 7) == 0b0:
        i += 1
      elif (byte_as_int >> 5) == 0b110:
        starts_with_0b10(bytes[i+1]) 
        i += 2
      elif (byte_as_int >> 4) == 0b1110:
        starts_with_0b10(bytes[i+1]) 
        starts_with_0b10(bytes[i+2]) 
        i += 3
      elif (byte_as_int >> 3) == 0b11110:
        starts_with_0b10(bytes[i+1]) 
        starts_with_0b10(bytes[i+2]) 
        starts_with_0b10(bytes[i+3])
        i += 4
      else:
        return INVALID_START
    except IndexError:
      return INCOMPLETE
    except RuntimeError:
      return INVALID_CONT

    num_utf8_chars += 1

  return num_utf8_chars

def starts_with_0b10(byte):
  if (ord(byte) >> 6) != 0b10:
    raise RuntimeError

# Implementation without Python regex: #
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
    self.replace_str = replace_str

  def Replace(self, s, op):
    if op.do_all:
      return s.replace(self.pat, self.replace_str)
    elif op.do_prefix:
      if s.startswith(self.pat):
        n = len(self.pat)
        return self.replace_str + s[n:]
      else:
        return s
    elif op.do_suffix:
      if s.endswith(self.pat):
        n = len(self.pat)
        return s[:-n] + self.replace_str
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
