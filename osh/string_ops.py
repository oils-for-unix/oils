"""
string_ops.py - String library functions that can be exposed with a saner syntax.

OSH:

    local y=${x//a*/b}

YSH:

    var y = x => sub('a*', 'b', :ALL)

    Pass x => sub('a*', 'b', :ALL) => var y
"""

from _devbuild.gen.id_kind_asdl import Id
from _devbuild.gen.syntax_asdl import loc, Token, suffix_op
from core import pyutil
from core import ui
from core import error
from core.error import e_die, e_strict
from mycpp.mylib import log
from mycpp import mylib
from osh import glob_

import libc
import fastfunc

from typing import List, Tuple

_ = log

# TODO: Add details of the invalid character/byte here?

INCOMPLETE_CHAR = 'Incomplete UTF-8 character'
INVALID_CONT = 'Invalid UTF-8 continuation byte'
INVALID_START = 'Invalid start of UTF-8 character'

# Error types returned by fastfunc.Utf8DecodeOne
# Derived from Utf8Error enum from data_lang/utf8.h
UTF8_ERR_OVERLONG = -1  # Encodes a codepoint in more bytes than necessary
UTF8_ERR_SURROGATE = -2  # Encodes a codepoint in the surrogate range (0xD800 to 0xDFFF)
UTF8_ERR_TOO_LARGE = -3  # Encodes a value greater than the max codepoint U+10FFFF
UTF8_ERR_BAD_ENCODING = -4  # Encoding doesn't conform to the UTF-8 bit patterns
UTF8_ERR_TRUNCATED_BYTES = -5  # It looks like there is another codepoint, but it has been truncated
UTF8_ERR_END_OF_STREAM = -6  # We are at the end of the string. (input_len = 0)


def Utf8Error_str(error):
    # type: (int) -> str
    if error == UTF8_ERR_OVERLONG:
        return "Utf8 Error: Decoded Overlong"
    if error == UTF8_ERR_SURROGATE:
        return "Utf8 Error: Decoded Surrogate"
    if error == UTF8_ERR_TOO_LARGE:
        return "Utf8 Error: Decoded Invalid Codepoint"
    if error == UTF8_ERR_BAD_ENCODING:
        return "Utf8 Error: Bad Encoding"
    if error == UTF8_ERR_TRUNCATED_BYTES:
        return "Utf8 Error: Truncated Bytes"
    if error == UTF8_ERR_END_OF_STREAM:
        return "Utf8 Error: End of Stream"

    raise AssertionError(0)


def _CheckContinuationByte(byte):
    # type: (str) -> None
    if (ord(byte) >> 6) != 0b10:
        e_strict(INVALID_CONT, loc.Missing)


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
        e_strict(INVALID_START, loc.Missing)


def DecodeUtf8Char(s, start):
    # type: (str, int) -> int
    """Given a string and start index, decode the Unicode char immediately
    following the start index. The start location is in bytes and should be
    found using a function like NextUtf8Char or PreviousUtf8Char.

    If the codepoint in invalid, we raise an `error.Expr`. (This is different
    from {Next,Previous}Utf8Char which raises an `error.Strict` on encoding
    errors.)
    """
    # The data_lang/utf8.h decoder treats nul-bytes as an end of string
    # sentinel. However, they may not be the end of the string here. So we must
    # special case the nul-byte.
    if mylib.ByteAt(s, start) == 0:
        return 0

    codepoint_or_error, bytes_read = fastfunc.Utf8DecodeOne(s, start)
    if codepoint_or_error < 0:
        raise error.Expr(
            "%s at %d" % (Utf8Error_str(codepoint_or_error), start + bytes_read),
            loc.Missing)
    return codepoint_or_error


def NextUtf8Char(s, i):
    # type: (str, int) -> int
    """Given a string and a byte offset, returns the byte position after the
    character at this position.  Usually this is the position of the next
    character, but for the last character in the string, it's the position just
    past the end of the string.

    Validates UTF-8.
    """
    # Like in DecodeUtf8Char, this must be special-cased.
    if mylib.ByteAt(s, i) == 0:
        return 1

    codepoint_or_error, bytes_read = fastfunc.Utf8DecodeOne(s, i)
    if codepoint_or_error < 0:
        e_strict("%s at %d" % (Utf8Error_str(codepoint_or_error), i), loc.Missing)
    return i + bytes_read


def PreviousUtf8Char(s, i):
    # type: (str, int) -> int
    """Given a string and a byte offset, returns the position of the character
    before that offset.  To start (find the first byte of the last character),
    pass len(s) for the initial value of i.

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
        byte_as_int = mylib.ByteAt(s, i)
        if (byte_as_int >> 6) != 0b10:
            offset = orig_i - i
            if offset != _Utf8CharLen(byte_as_int):
                # Leaving a generic error for now, but if we want to, it's not
                # hard to calculate the position where things go wrong.  Note
                # that offset might be more than 4, for an invalid utf-8 string.
                e_strict(INVALID_START, loc.Missing)
            return i

    e_strict(INVALID_START, loc.Missing)


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
        i = NextUtf8Char(s, i)
        num_chars += 1
    return num_chars


def AdvanceUtf8Chars(s, num_chars, byte_offset):
    # type: (str, int, int) -> int
    """Starting from byte offset, advance by N UTF-8 runes

    Returns a byte offset.

    Used for shell slicing.
    """
    num_bytes = len(s)
    i = byte_offset  # current byte position

    for _ in xrange(num_chars):
        # Neither bash or zsh checks out of bounds for slicing.  Either begin or
        # length.
        if i >= num_bytes:
            return i
            #raise RuntimeError('Out of bounds')

        i = NextUtf8Char(s, i)

    return i


# Limited Unicode codepoints for whitespace characters.
# Oils intentionally does not include characters from <USP>, as that set
# depends on the version of the Unicode standard used.
#
# See discussion on the original pull request which added this list here:
#
#   https://github.com/oilshell/oil/pull/1836#issuecomment-1942173520
#
# See also the Mozilla Javascript documentation, and the note on how
# changes to the standard affected Javascript:
#
#     https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Lexical_grammar#white_space

SPACES = [
    0x0009,  # Horizontal tab (\t)
    0x000A,  # Newline (\n)
    0x000B,  # Vertical tab (\v)
    0x000C,  # Form feed (\f)
    0x000D,  # Carriage return (\r)
    0x0020,  # Normal space
    0x00A0,  # No-break space <NBSP>
    0xFEFF,  # Zero-width no-break space <ZWNBSP>
]


def _IsSpace(codepoint):
    # type: (int) -> bool
    return codepoint in SPACES


def StartsWithWhitespaceByteRange(s):
    # type: (str) -> Tuple[int, int]
    """Returns the range of 's' which has leading whitespace characters.

    If 's' has no leading whitespace, an valid but empty range is returned.

    The returned range is given as byte positions, and is a half-open range
    "[start, end)" which is returned as a tuple.

    Used for shell functions like 'trimStart' to match then trim whitespace.
    """
    len_s = len(s)
    i = 0
    while i < len_s:
        codepoint = DecodeUtf8Char(s, i)
        if not _IsSpace(codepoint):
            break

        try:
            i = NextUtf8Char(s, i)
        except error.Strict:
            assert False, "DecodeUtf8Char should have caught any encoding errors"

    start = 0
    end = i
    return (start, end)


def EndsWithWhitespaceByteRange(s):
    # type: (str) -> Tuple[int, int]
    """Returns the range of 's' which has trailing whitespace characters.

    If 's' has no leading whitespace, an valid but empty range is returned.

    The returned range is given as byte positions, and is a half-open range
    "[start, end)" which is returned as a tuple.

    Used for shell functions like 'trimEnd' to match then trim whitespace.
    """
    len_s = len(s)
    i = len_s
    while i > 0:
        # TODO: Gracefully handle surrogate pairs and overlong encodings when
        # finding the start of each character.
        prev = PreviousUtf8Char(s, i)

        codepoint = DecodeUtf8Char(s, prev)
        if not _IsSpace(codepoint):
            break

        i = prev

    start = i
    end = len_s
    return (start, end)


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
#                       match prefixes, it matches EXACTLY.
# - % shortest suffix - [-1:] [-2:] [-3:] ...
# - %% longest suffix - [1:] [2:] [3:]
#
# See remove_pattern() in subst.c for bash, and trimsub() in eval.c for
# mksh.  Dash doesn't implement it.

# TODO:
# - Unicode support: Convert both pattern, string, and replacement to unicode,
#   then the result back at the end.
# - Compile time errors for [[:space:]] ?


def DoUnarySuffixOp(s, op_tok, arg, is_extglob):
    # type: (str, Token, str, bool) -> str
    """Helper for ${x#prefix} and family."""

    id_ = op_tok.id

    # Fast path for constant strings.
    # TODO: Should be LooksLikeExtendedGlob!
    if not is_extglob and not glob_.LooksLikeGlob(arg):
        # It doesn't look like a glob, but we glob-escaped it (e.g. [ -> \[).  So
        # reverse it.  NOTE: We also do this check in Globber.Expand().  It would
        # be nice to somehow store the original string rather than
        # escaping/unescaping.
        arg = glob_.GlobUnescape(arg)

        if id_ in (Id.VOp1_Pound, Id.VOp1_DPound):  # const prefix
            # explicit check for non-empty arg (len for mycpp)
            if len(arg) and s.startswith(arg):
                return s[len(arg):]
            else:
                return s

        elif id_ in (Id.VOp1_Percent, Id.VOp1_DPercent):  # const suffix
            # need explicit check for non-empty arg (len for mycpp)
            if len(arg) and s.endswith(arg):
                return s[:-len(arg)]
            else:
                return s

        # These operators take glob arguments, we don't implement that obscure case.
        elif id_ == Id.VOp1_Comma:  # Only lowercase the first letter
            if arg != '':
                e_die("%s can't have an argument" % ui.PrettyId(id_), op_tok)
            if len(s):
                return s[0].lower() + s[1:]
            else:
                return s

        elif id_ == Id.VOp1_DComma:
            if arg != '':
                e_die("%s can't have an argument" % ui.PrettyId(id_), op_tok)
            return s.lower()

        elif id_ == Id.VOp1_Caret:  # Only uppercase the first letter
            if arg != '':
                e_die("%s can't have an argument" % ui.PrettyId(id_), op_tok)
            if len(s):
                return s[0].upper() + s[1:]
            else:
                return s

        elif id_ == Id.VOp1_DCaret:
            if arg != '':
                e_die("%s can't have an argument" % ui.PrettyId(id_), op_tok)
            return s.upper()

        else:  # e.g. ^ ^^ , ,,
            raise AssertionError(id_)

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

    if id_ == Id.VOp1_Pound:  # shortest prefix
        # 'abcd': match '', 'a', 'ab', 'abc', ...
        i = 0
        while True:
            assert i <= n
            #log('Matching pattern %r with %r', arg, s[:i])
            if libc.fnmatch(arg, s[:i]):
                return s[i:]
            if i >= n:
                break
            i = NextUtf8Char(s, i)
        return s

    elif id_ == Id.VOp1_DPound:  # longest prefix
        # 'abcd': match 'abc', 'ab', 'a'
        i = n
        while True:
            assert i >= 0
            #log('Matching pattern %r with %r', arg, s[:i])
            if libc.fnmatch(arg, s[:i]):
                return s[i:]
            if i == 0:
                break
            i = PreviousUtf8Char(s, i)
        return s

    elif id_ == Id.VOp1_Percent:  # shortest suffix
        # 'abcd': match 'abcd', 'abc', 'ab', 'a'
        i = n
        while True:
            assert i >= 0
            #log('Matching pattern %r with %r', arg, s[:i])
            if libc.fnmatch(arg, s[i:]):
                return s[:i]
            if i == 0:
                break
            i = PreviousUtf8Char(s, i)
        return s

    elif id_ == Id.VOp1_DPercent:  # longest suffix
        # 'abcd': match 'abc', 'bc', 'c', ...
        i = 0
        while True:
            assert i <= n
            #log('Matching pattern %r with %r', arg, s[:i])
            if libc.fnmatch(arg, s[i:]):
                return s[:i]
            if i >= n:
                break
            i = NextUtf8Char(s, i)
        return s

    else:
        raise NotImplementedError(ui.PrettyId(id_))


def _AllMatchPositions(s, regex):
    # type: (str, str) -> List[Tuple[int, int]]
    """Returns a list of all (start, end) match positions of the regex against
    s.

    (If there are no matches, it returns the empty list.)
    """
    matches = []  # type: List[Tuple[int, int]]
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
    parts = []  # type: List[str]
    prev_end = 0
    for start, end in _AllMatchPositions(s, regex):
        parts.append(s[prev_end:start])
        parts.append(replace_str)
        prev_end = end
    parts.append(s[prev_end:])
    return ''.join(parts)


class GlobReplacer(object):

    def __init__(self, regex, replace_str, slash_tok):
        # type: (str, str, Token) -> None

        # TODO: It would be nice to cache the compilation of the regex here,
        # instead of just the string.  That would require more sophisticated use of
        # the Python/C API in libc.c, which we might want to avoid.
        self.regex = regex
        self.replace_str = replace_str
        self.slash_tok = slash_tok

    def __repr__(self):
        # type: () -> str
        return '<_GlobReplacer regex %r r %r>' % (self.regex, self.replace_str)

    def Replace(self, s, op):
        # type: (str, suffix_op.PatSub) -> str

        regex = '(%s)' % self.regex  # make it a group

        if op.replace_mode == Id.Lit_Slash:
            # Avoid infinite loop when replacing all copies of empty string
            if len(self.regex) == 0:
                return s

            try:
                return _PatSubAll(s, regex,
                                  self.replace_str)  # loop over matches
            except RuntimeError as e:
                # Not sure if this is possible since we convert from glob:
                # libc.regex_first_group_match raises RuntimeError on regex syntax
                # error.
                msg = e.message  # type: str
                e_die('Error matching regex %r: %s' % (regex, msg),
                      self.slash_tok)

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


def ShellQuoteB(s):
    # type: (str) -> str
    """Quote by adding backslashes.

    Used for autocompletion, so it's friendlier for display on the
    command line. We use the strategy above for other use cases.
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
    return pyutil.BackslashEscape(s, ' `~!$&*()[]{}\\|;\'"<>?')
