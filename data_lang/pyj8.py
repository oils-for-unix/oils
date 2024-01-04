#!/usr/bin/env python2
from __future__ import print_function

from _devbuild.gen.id_kind_asdl import Id, Id_t, Id_str
from core import error
from frontend import consts
from frontend import match
from mycpp import mylib
from mycpp.mylib import log

from typing import Tuple, List, Optional

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
_JSON_ESCAPES = {
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
        escaped = _JSON_ESCAPES.get(ch)
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
        buf.write('"')
        _EscapeUnprintable(s, buf)
        buf.write('"')

    return 0


class LexerDecoder(object):
    """J8 lexer and string decoder.

    Similar interface as SimpleLexer2, except we return an optional decoded
    string

    TODO: Combine

    match.J8Lexer
    match.J8StrLexer

    When you hit "" b'' u''

    1. Start the string lexer
    2. decode it in place
    3. validate utf-8 on the Id.Char_Literals tokens -- these are the only ones
       that can be arbitrary strings
    4. return decoded string
    """

    def __init__(self, s):
        # type: (str) -> None
        self.s = s
        self.pos = 0
        # Reuse this instance to save GC objects.  JSON objects could have
        # thousands of strings.
        self.decoded = mylib.BufWriter()

    def _Error(self, msg, end_pos):
        # type: (str, int) -> error.Decode

        # Use the current position as start pos
        return error.Decode(msg, self.s, self.pos, end_pos)

    def Next(self):
        # type: () -> Tuple[Id_t, int, Optional[str]]

        while True:  # ignore spaces
            tok_id, end_pos = match.MatchJ8Token(self.s, self.pos)
            if tok_id != Id.Ignored_Space:
                break
            self.pos = end_pos

        # TODO: Distinguish bewteen "" b'' and u'', and allow different
        # escapes.
        if tok_id not in (Id.Left_DoubleQuote, Id.Left_USingleQuote,
                          Id.Left_BSingleQuote):
            self.pos = end_pos
            return tok_id, end_pos, None

        return self._DecodeString(tok_id, end_pos)

    def _DecodeString(self, left_id, str_pos):
        # type: (Id_t, int) -> Tuple[Id_t, int, Optional[str]]

        # TODO: break dep
        from osh import string_ops

        while True:
            if left_id == Id.Left_DoubleQuote:
                tok_id, str_end = match.MatchJsonStrToken(self.s, str_pos)
            else:
                tok_id, str_end = match.MatchJ8StrToken(self.s, str_pos)

            if tok_id == Id.Eol_Tok:
                # TODO: point to beginning of # quote?
                raise self._Error('Unexpected EOF while lexing JSON string',
                                  str_end)
            if tok_id == Id.Unknown_Tok:
                # e.g. invalid backslash
                raise self._Error('Unknown token while lexing JSON string',
                                  str_end)
            if tok_id == Id.Char_AsciiControl:
                raise self._Error(
                    "ASCII control chars are illegal in JSON strings", str_end)

            if tok_id in (Id.Right_SingleQuote, Id.Right_DoubleQuote):

                self.pos = str_end

                s = self.decoded.getvalue()
                #log('s %r', s)
                # This doesn't do what we think
                #self.decoded.reset()

                if 0:
                    # Reusing this object is more efficient, e.g. with a
                    # payload with thousands of strings
                    mylib.ClearBuf(self.decoded)
                else:
                    self.decoded = mylib.BufWriter()

                #log('decoded %r', self.decoded.getvalue())
                return Id.J8_AnyString, str_end, s

            #
            # Now handle each kind of token
            #

            if tok_id == Id.Char_Literals:  # JSON and J8
                part = self.s[str_pos:str_end]
                try:
                    part.decode('utf-8')
                except UnicodeDecodeError as e:
                    # Syntax error because JSON must be valid UTF-8
                    # Limit context to 20 chars arbitrarily
                    raise self._Error(
                        'Invalid UTF-8 in JSON string literal: %r' % part[:20],
                        str_end)

            # TODO: would be nice to avoid allocation in all these cases.
            # But LookupCharC() would have to change.

            elif tok_id == Id.Char_OneChar:  # JSON and J8
                ch = self.s[str_pos + 1]
                part = consts.LookupCharC(ch)

            elif tok_id == Id.Char_UBraced:  # J8 only
                h = self.s[str_pos + 3:str_end - 1]
                i = int(h, 16)
                part = string_ops.Utf8Encode(i)

            elif tok_id == Id.Char_YHex:  # J8 only
                h = self.s[str_pos + 2:str_end]
                i = int(h, 16)
                part = chr(i)

            elif tok_id == Id.Char_Unicode4:  # JSON only
                h = self.s[str_pos + 2:str_end]
                i = int(h, 16)
                part = string_ops.Utf8Encode(i)

            else:
                # Should never happen
                raise AssertionError(Id_str(tok_id))

            #log('%s part %r', Id_str(tok_id), part)
            self.decoded.write(part)
            str_pos = str_end


# vim: sw=4
