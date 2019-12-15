"""
string_ops.py - String library functions that can be exposed with a saner syntax.

Instead of:

    local y=${x//a*/b}
    var y = x -> sub('a*', 'b', :ALL)
    var y = x -> sub( Glob/a*/, 'b', :ALL)  # maybe a glob literal
"""

from _devbuild.gen.id_kind_asdl import Id
from core import error
from core import util
from core.util import e_die
from osh import glob_

import libc

from typing import List, Tuple, TYPE_CHECKING
if TYPE_CHECKING:
  from _devbuild.gen.syntax_asdl import suffix_op__Unary, suffix_op__PatSub


def Utf8Encode(code):
  # type: (int) -> str
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
  # type: (str) -> None
  if (ord(byte) >> 6) != 0b10:
    raise error.InvalidUtf8(INVALID_CONT)


def _Utf8CharLen(starting_byte):
  # type: (int) -> int
  if (starting_byte >> 7) == 0b0:
    return 1
  elif (starting_byte >> 5) == 0b110:
    return 2
  elif (starting_byte >> 4) == 0b1110:
    return 3
  elif (starting_byte >> 3) == 0b11110:
    return 4
  else:
    raise error.InvalidUtf8(INVALID_START)


def _NextUtf8Char(s, i):
  # type: (str, int) -> int
  """
  Given a string and a byte offset, returns the byte position after
  the character at this position.  Usually this is the position of the
  next character, but for the last character in the string, it's the
  position just past the end of the string.

  Validates UTF-8.
  """
  byte_as_int = ord(s[i])  # Should never raise IndexError

  try:
    length = _Utf8CharLen(byte_as_int)
    for j in xrange(i + 1, i + length):
      _CheckContinuationByte(s[j])
    i += length
  except IndexError:
    raise error.InvalidUtf8(INCOMPLETE_CHAR)

  return i


def _PreviousUtf8Char(s, i):
  # type: (str, int) -> int
  """
  Given a string and a byte offset, returns the position of the
  character before that offset.  To start (find the first byte of the
  last character), pass len(s) for the initial value of i.

  Validates UTF-8.
  """
  # All bytes in a valid UTF-8 string have one of the following formats:
  #
  #   0xxxxxxx (1-byte char)
  #   110xxxxx (start of 2-byte char)
  #   1110xxxx (start of 3-byte char)
  #   11110xxx (start of 4-byte char)
  #   10xxxxxx (continuation byte)
  #
  # Any byte that starts with 10... MUST be a continuation byte,
  # otherwise it must be the start of a character (or just invalid
  # data).
  #
  # Walking backward, we stop at the first non-continuaton byte
  # found.  We try to interpret it as a valid UTF-8 character starting
  # byte, and check that it indicates the correct length, based on how
  # far we've moved from the original byte.  Possible problems:
  #   * byte we stopped on does not have a valid value (e.g., 11111111)
  #   * start byte indicates more or fewer continuation bytes than we've seen
  #   * no start byte at beginning of array
  #
  # Note that because we are going backward, on malformed input, we
  # won't error out in the same place as when parsing the string
  # forwards as normal.
  orig_i = i

  while i > 0:
    i -= 1
    byte_as_int = ord(s[i])
    if (byte_as_int >> 6) != 0b10:
      offset = orig_i - i
      if offset != _Utf8CharLen(byte_as_int):
        # Leaving a generic error for now, but if we want to, it's not
        # hard to calculate the position where things go wrong.  Note
        # that offset might be more than 4, for an invalid utf-8 string.
        raise error.InvalidUtf8(INVALID_START)
      return i

  raise error.InvalidUtf8(INVALID_START)


def CountUtf8Chars(s):
  # type: (str) -> int
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
  # type: (str, int, int) -> int
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
  # type: (str, suffix_op__Unary, str) -> str
  """Helper for ${x#prefix} and family."""

  # Fast path for constant strings.
  if not glob_.LooksLikeGlob(arg):
    # It doesn't look like a glob, but we glob-escaped it (e.g. [ -> \[).  So
    # reverse it.  NOTE: We also do this check in Globber.Expand().  It would
    # be nice to somehow store the original string rather tahn
    # escaping/unescaping.
    arg = glob_.GlobUnescape(arg)

    if op.op_id in (Id.VOp1_Pound, Id.VOp1_DPound):  # const prefix
      # explicit check for non-empty arg (len for mycpp)
      if len(arg) and s.startswith(arg):
        return s[len(arg):]
      else:
        return s

    elif op.op_id in (Id.VOp1_Percent, Id.VOp1_DPercent):  # const suffix
      # need explicit check for non-empty arg (len for mycpp)
      if len(arg) and s.endswith(arg):
        return s[:-len(arg)]
      else:
        return s

    # These operators take glob arguments, we don't implement that obscure case.
    elif op.op_id == Id.VOp1_Comma:  # Only lowercase the first letter
      if arg != '':
        raise NotImplementedError("%s can't have an argument" % op.op_id)
      if len(s):
        return s[0].lower() + s[1:]
      else:
        return s

    elif op.op_id == Id.VOp1_DComma:
      if arg != '':
        raise NotImplementedError("%s can't have an argument" % op.op_id)
      return s.lower()

    elif op.op_id == Id.VOp1_Caret:  # Only uppercase the first letter
      if arg != '':
        raise NotImplementedError("%s can't have an argument" % op.op_id)
      if len(s):
        return s[0].upper() + s[1:]
      else:
        return s

    elif op.op_id == Id.VOp1_DCaret:
      if arg != '':
        raise NotImplementedError("%s can't have an argument" % op.op_id)
      return s.upper()

    else:  # e.g. ^ ^^ , ,,
      raise AssertionError(op.op_id)

  # For patterns, do fnmatch() in a loop.
  #
  # TODO:
  # - Another potential fast path:
  #   v=aabbccdd
  #   echo ${v#*b}  # strip shortest prefix
  #
  # If the whole thing doesn't match '*b*', then no test can succeed.  So we
  # can fail early.  Conversely echo ${v%%c*} and '*c*'.
  #
  # (Although honestly this whole construct is nuts and should be deprecated.)

  n = len(s)

  if op.op_id == Id.VOp1_Pound:  # shortest prefix
    # 'abcd': match '', 'a', 'ab', 'abc', ...
    i = 0
    while True:
      assert i <= n
      #log('Matching pattern %r with %r', arg, s[:i])
      if libc.fnmatch(arg, s[:i]):
        return s[i:]
      if i >= n:
        break
      i = _NextUtf8Char(s, i)
    return s

  elif op.op_id == Id.VOp1_DPound:  # longest prefix
    # 'abcd': match 'abc', 'ab', 'a'
    i = n
    while True:
      assert i >= 0
      #log('Matching pattern %r with %r', arg, s[:i])
      if libc.fnmatch(arg, s[:i]):
        return s[i:]
      if i == 0:
        break
      i = _PreviousUtf8Char(s, i)
    return s

  elif op.op_id == Id.VOp1_Percent:  # shortest suffix
    # 'abcd': match 'abcd', 'abc', 'ab', 'a'
    i = n
    while True:
      assert i >= 0
      #log('Matching pattern %r with %r', arg, s[:i])
      if libc.fnmatch(arg, s[i:]):
        return s[:i]
      if i == 0:
        break
      i = _PreviousUtf8Char(s, i)
    return s

  elif op.op_id == Id.VOp1_DPercent:  # longest suffix
    # 'abcd': match 'abc', 'bc', 'c', ...
    i = 0
    while True:
      assert i <= n
      #log('Matching pattern %r with %r', arg, s[:i])
      if libc.fnmatch(arg, s[i:]):
        return s[:i]
      if i >= n:
        break
      i = _NextUtf8Char(s, i)
    return s

  else:
    raise NotImplementedError("Can't use %s with pattern" % op.op_id)


def _AllMatchPositions(s, regex):
  # type: (str, str) -> List[Tuple[int, int]]
  """Returns a list of all (start, end) match positions of the regex against s.

  (If there are no matches, it returns the empty list.)
  """
  matches = []
  pos = 0
  n = len(s)
  while pos < n:  # needed to prevent infinite loop in (.*) case
    m = libc.regex_first_group_match(regex, s, pos)
    if m is None:
      break
    matches.append(m)
    start, end = m
    pos = end  # advance position
  return matches


def _PatSubAll(s, regex, replace_str):
  # type: (str, str, str) -> str
  parts = []
  prev_end = 0
  for start, end in _AllMatchPositions(s, regex):
    parts.append(s[prev_end:start])
    parts.append(replace_str)
    prev_end = end
  parts.append(s[prev_end:])
  return ''.join(parts)


class GlobReplacer(object):

  def __init__(self, regex, replace_str, slash_spid):
    # type: (str, str, int) -> None

    # TODO: It would be nice to cache the compilation of the regex here,
    # instead of just the string.  That would require more sophisticated use of
    # the Python/C API in libc.c, which we might want to avoid.
    self.regex = regex
    self.replace_str = replace_str
    self.slash_spid = slash_spid

  def __repr__(self):
    # type: () -> str
    return '<_GlobReplacer regex %r r %r>' % (self.regex, self.replace_str)

  def Replace(self, s, op):
    # type: (str, suffix_op__PatSub) -> str

    regex = '(%s)' % self.regex  # make it a group

    if op.replace_mode == Id.Lit_Slash:
      try:
        return _PatSubAll(s, regex, self.replace_str)  # loop over matches
      except RuntimeError as e:
        e_die('Error matching regex %r: %s', regex, e, span_id=self.slash_spid)

    if op.replace_mode == Id.Lit_Pound:
      regex = '^' + regex
    elif op.replace_mode == Id.Lit_Percent:
      regex = regex + '$'

    m = libc.regex_first_group_match(regex, s, 0)
    #log('regex = %r, s = %r, match = %r', regex, s, m)
    if m is None:
      return s
    start, end = m
    return s[:start] + self.replace_str + s[end:]


# TODO: Replace with ShellQuoteOneLine?  It may need more testing and
# optimization.
def ShellQuote(s):
  # type: (str) -> str
  """Quote 's' in a way that can be reused as shell input.

  It doesn't necessarily match bash byte-for-byte.  IIRC bash isn't consistent
  with it anyway.

  Used for 'printf %q', ${x@Q}, and 'set'.
  """
  # Could be made slightly nicer by e.g. returning unmodified when
  # there's nothing that needs to be quoted.  Bash's `printf %q`
  # does that while producing uglier output in other ways, with
  # lots of backslashes.  Hopefully we don't end up having to
  # match its behavior byte-for-byte.
  #
  # Example: FOO'BAR -> 'FOO'\''BAR'
  return "'" + s.replace("'", r"'\''") + "'"


def ShellQuoteOneLine(s):
  # type: (str) -> str

  # TODO: Could use a regex to speed this up
  needs_dollar = False
  for c in s:
    if c in "'\t\r\n":
      needs_dollar = True
      break

  if needs_dollar:
    escaped = (s
        .replace('\\', '\\\\')
        .replace("'", "\\'")
        .replace('\t', '\\t')
        .replace('\r', '\\r')
        .replace('\n', '\\n'))
    return "$'" + escaped + "'"
  else:
    return "'" + s + "'"


def ShellQuoteB(s):
  # type: (str) -> str
  """Quote by adding backslashes.

  Used for autocompletion, so it's friendlier for display on the command line.
  We use the strategy above for other use cases.
  """
  # There's no way to escape a newline!  Bash prints ^J for some reason, but
  # we're more explicit.  This will happen if there's a newline on a file
  # system or a completion plugin returns a newline.

  # NOTE: tabs CAN be escaped with \.
  s = s.replace('\r', '<INVALID CR>').replace('\n', '<INVALID NEWLINE>')

  # ~ for home dir
  # ! for history
  # * [] ? for glob
  # {} for brace expansion
  # space because it separates words
  return util.BackslashEscape(s, ' `~!$&*()[]{}\\|;\'"<>?')

