"""data_lang/htm8.py

TODO

Migrate:

- maybe: migrate everything off of TagLexer() 
  - and AttrValueLexer() - this should requires Validate()

API:
- Get rid of Reset()?
- Deprecate tag_lexer.GetTagName() in favor of lx.CanonicalTagName() or
  _LiteralTagName()
- UTF-8 check, like JSON8
- re2c
  - port lexer, which will fix static typing issues
  - the abstraction needs to support submatch?
    - for finding the end of a tag, etc.?
  - and what about no match?

- harmonize LexError and ParseError with data_lang/j8.py, which uses
  error.Decode(msg, ..., cur_line_num)

- Copy all errors into doc/ref/chap-errors.md
  - This helps understand the language

- Update doc/htm8.md
- list of Algorithms:
  - lex just the top level
  - lex both levels
  - and match tags - this is the level for value.Htm8Frag?
  - convert to XML!
  - lazy selection by tag, or attr (id= and class=)
  - lazy selection by CSS selector expression
  - convert to DOMTree
  - sed-like replacement of DOM Tree or element
  - untrusted HTML filter, e.g. like StackOverflow / Reddit
    - this is Safe HTM8
    - should have a zero alloc way to support this, with good errors?
      - I think most of them silently strip data
"""

import re

from typing import Dict, List, Tuple, Optional, IO, Iterator, Any

from _devbuild.gen.htm8_asdl import (h8_id, h8_id_t, h8_tag_id, h8_tag_id_t,
                                     h8_tag_id_str, attr_name, attr_name_t,
                                     attr_name_str, attr_value_e, attr_value_t,
                                     h8_val_id)
from doctools.util import log


class LexError(Exception):
    """
    Examples of lex errors:

    - h8_id.Invalid, like <> or &&
    - Unclosed <!--  <?  <![CDATA[  <script>  <style>
    """

    def __init__(self, msg, code_str, start_pos):
        # type: (str, str, int) -> None
        self.msg = msg
        self.code_str = code_str
        self.start_pos = start_pos

    def __str__(self):
        # type: () -> str
        return '(LexError %r %r)' % (
            self.msg, self.code_str[self.start_pos:self.start_pos + 20])


def _FindLineNum(s, error_pos):
    # type: (str, int) -> int
    current_pos = 0
    line_num = 1
    while True:
        newline_pos = s.find('\n', current_pos)
        #log('current = %d, N %d, line %d', current_pos, newline_pos, line_num)

        if newline_pos == -1:  # this is the last line
            return line_num
        if newline_pos >= error_pos:
            return line_num
        line_num += 1
        current_pos = newline_pos + 1


class ParseError(Exception):
    """
    Examples of parse errors

    - unbalanced tag structure
    - ul_table.py errors
    """

    def __init__(self, msg, s=None, start_pos=-1):
        # type: (str, Optional[str], int) -> None
        self.msg = msg
        self.s = s
        self.start_pos = start_pos

    def __str__(self):
        # type: () -> str
        if self.s is not None:
            assert self.start_pos != -1, self.start_pos
            snippet = (self.s[self.start_pos:self.start_pos + 20])

            line_num = _FindLineNum(self.s, self.start_pos)
        else:
            snippet = ''
            line_num = -1
        msg = 'line %d: %r %r' % (line_num, self.msg, snippet)
        return msg


class Output(object):
    """Output for sed-like "replacement" model.

    Takes an underlying input buffer and an output file.  Maintains a position
    in the input buffer.

    Print FROM the input or print new text to the output.
    """

    def __init__(self, s, f, left_pos=0, right_pos=-1):
        # type: (str, IO[str], int, int) -> None
        self.s = s
        self.f = f
        self.pos = left_pos
        self.right_pos = len(s) if right_pos == -1 else right_pos

    def SkipTo(self, pos):
        # type: (int) -> None
        """Skip to a position."""
        self.pos = pos

    def PrintUntil(self, pos):
        # type: (int) -> None
        """Print until a position."""
        piece = self.s[self.pos:pos]
        self.f.write(piece)
        self.pos = pos

    def PrintTheRest(self):
        # type: () -> None
        """Print until the end of the string."""
        self.PrintUntil(self.right_pos)

    def Print(self, s):
        # type: (str) -> None
        """Print text to the underlying buffer."""
        self.f.write(s)


def MakeLexer(rules):
    return [(re.compile(pat, re.VERBOSE), i) for (pat, i) in rules]


#
# Lexers
#

_NAME = r'[a-zA-Z][a-zA-Z0-9:_\-]*'  # must start with letter

CHAR_LEX = [
    # Characters
    # https://www.w3.org/TR/xml/#sec-references
    (r'&\# [0-9]+ ;', h8_id.DecChar),
    (r'&\# x[0-9a-fA-F]+ ;', h8_id.HexChar),
    (r'& %s ;' % _NAME, h8_id.CharEntity),
    # Allow unquoted, and quoted
    (r'&', h8_id.BadAmpersand),
]

HTM8_LEX = CHAR_LEX + [
    # TODO: CommentBegin, ProcessingBegin, CDataBegin could have an additional
    # action associated with them?  The ending substring
    (r'<!--', h8_id.CommentBegin),

    # Processing instruction are used for the XML header:
    # <?xml version="1.0" encoding="UTF-8"?>
    # They are technically XML-only, but in HTML5, they are another kind of
    # comment:
    #
    #   https://developer.mozilla.org/en-US/docs/Web/API/ProcessingInstruction
    #
    (r'<\?', h8_id.ProcessingBegin),
    # Not necessary in HTML5, but occurs in XML
    (r'<!\[CDATA\[', h8_id.CDataBegin),  # <![CDATA[

    # Markup declarations
    # - In HTML5, there is only <!DOCTYPE html>
    # - XML has 4 more declarations: <!ELEMENT ...> ATTLIST ENTITY NOTATION
    #   - these seem to be part of DTD
    #   - it's useful to skip these, and be able to parse the rest of the document
    # - Note: < is allowed?
    (r'<! [^>\x00]+ >', h8_id.Decl),

    # Tags
    # Notes:
    # - We look for a valid tag name, but we don't validate attributes.
    #   That's done in the tag lexer.
    # - We don't allow leading whitespace
    (r'</ (%s) >' % _NAME, h8_id.EndTag),
    # self-closing <br/>  comes before StartTag
    # could/should these be collapsed into one rule?
    (r'<  (%s) [^>\x00]* />' % _NAME, h8_id.StartEndTag),  # end </a>
    (r'<  (%s) [^>\x00]* >' % _NAME, h8_id.StartTag),  # start <a>

    # HTML5 allows unescaped > in raw data, but < is not allowed.
    # https://stackoverflow.com/questions/10462348/right-angle-bracket-in-html
    #
    # - My early blog has THREE errors when disallowing >
    # - So do some .wwz files
    (r'[^&<>\x00]+', h8_id.RawData),
    (r'>', h8_id.BadGreaterThan),
    # NUL is the end, an accomodation for re2c.  Like we do in frontend/match.
    (r'\x00', h8_id.EndOfStream),
    # This includes < - it is not BadLessThan because it's NOT recoverable
    (r'.', h8_id.Invalid),
]

# Old notes:
#
# Non-greedy matches are regular and can be matched in linear time
# with RE2.
#
# https://news.ycombinator.com/item?id=27099798
#

# This person tried to do it with a regex:
#
# https://skeptric.com/html-comment-regexp/index.html

# . is any char except newline
# https://re2c.org/manual/manual_c.html

# Discarded options
#(r'<!-- .*? -->', h8_id.Comment),

# Hack from Claude: \s\S instead of re.DOTALL.  I don't like this
#(r'<!-- [\s\S]*? -->', h8_id.Comment),
#(r'<!-- (?:.|[\n])*? -->', h8_id.Comment),

HTM8_LEX_COMPILED = MakeLexer(HTM8_LEX)


class Lexer(object):

    def __init__(self, s, left_pos=0, right_pos=-1, no_special_tags=False):
        # type: (str, int, int, bool) -> None
        self.s = s
        self.pos = left_pos
        self.right_pos = len(s) if right_pos == -1 else right_pos
        self.no_special_tags = no_special_tags

        # string -> compiled regex pattern object
        self.cache = {}  # type: Dict[str, Any]

        # either </script> or </style> - we search until we see that
        self.search_state = None  # type: Optional[str]

        # Position of tag name, if applicable
        # - Set after you get a StartTag, EndTag, or StartEndTag
        # - Unset on other tags
        self.tag_pos_left = -1
        self.tag_pos_right = -1

    def _Read(self):
        # type: () -> Tuple[h8_id_t, int]
        if self.pos == self.right_pos:
            return h8_id.EndOfStream, self.pos

        assert self.pos < self.right_pos, self.pos

        if self.search_state is not None and not self.no_special_tags:
            # TODO: case-insensitive search for </SCRIPT> <SCRipt> ?
            #
            # Another strategy: enter a mode where we find ONLY the end tag
            # regex, and any data that's not <, and then check the canonical
            # tag name for 'script' or 'style'.
            pos = self.s.find(self.search_state, self.pos)
            if pos == -1:
                raise LexError('Unterminated <script> or <style>', self.s,
                               self.pos)
            self.search_state = None
            # beginning
            return h8_id.HtmlCData, pos

        # Find the first match.
        # Note: frontend/match.py uses _LongestMatch(), which is different!
        # TODO: reconcile them.  This lexer should be expressible in re2c.

        for pat, tok_id in HTM8_LEX_COMPILED:
            m = pat.match(self.s, self.pos)
            if m:
                if tok_id in (h8_id.StartTag, h8_id.EndTag, h8_id.StartEndTag):
                    self.tag_pos_left = m.start(1)
                    self.tag_pos_right = m.end(1)
                else:
                    # Reset state
                    self.tag_pos_left = -1
                    self.tag_pos_right = -1

                if tok_id == h8_id.CommentBegin:
                    pos = self.s.find('-->', self.pos)
                    if pos == -1:
                        raise LexError('Unterminated <!--', self.s, self.pos)
                    return h8_id.Comment, pos + 3  # -->

                if tok_id == h8_id.ProcessingBegin:
                    pos = self.s.find('?>', self.pos)
                    if pos == -1:
                        raise LexError('Unterminated <?', self.s, self.pos)
                    return h8_id.Processing, pos + 2  # ?>

                if tok_id == h8_id.CDataBegin:
                    pos = self.s.find(']]>', self.pos)
                    if pos == -1:
                        # unterminated <![CDATA[
                        raise LexError('Unterminated <![CDATA[', self.s,
                                       self.pos)
                    return h8_id.CData, pos + 3  # ]]>

                if tok_id == h8_id.StartTag:
                    # TODO: reduce allocations
                    if (self.TagNameEquals('script') or
                            self.TagNameEquals('style')):
                        # <SCRipt a=b>  -> </SCRipt>
                        self.search_state = '</' + self._LiteralTagName() + '>'

                return tok_id, m.end()
        else:
            raise AssertionError('h8_id.Invalid rule should have matched')

    def TagNamePos(self):
        # type: () -> int
        """The right position of the tag pos"""
        assert self.tag_pos_right != -1, self.tag_pos_right
        return self.tag_pos_right

    def TagNameEquals(self, expected):
        # type: (str) -> bool
        assert self.tag_pos_left != -1, self.tag_pos_left
        assert self.tag_pos_right != -1, self.tag_pos_right

        # TODO: In C++, this does not need an allocation.  Can we test
        # directly?
        return expected == self.CanonicalTagName()

    def _LiteralTagName(self):
        # type: () -> str
        assert self.tag_pos_left != -1, self.tag_pos_left
        assert self.tag_pos_right != -1, self.tag_pos_right

        return self.s[self.tag_pos_left:self.tag_pos_right]

    def CanonicalTagName(self):
        # type: () -> str
        tag_name = self._LiteralTagName()
        # Most tags are already lower case, so avoid allocation with this conditional
        # TODO: this could go in the mycpp runtime?
        if tag_name.islower():
            return tag_name
        else:
            return tag_name.lower()

    def Read(self):
        # type: () -> Tuple[h8_id_t, int]
        tok_id, end_pos = self._Read()
        self.pos = end_pos  # advance
        return tok_id, end_pos

    def LookAhead(self, regex):
        # type: (str) -> bool
        """
        Currently used for ul_table.py.  But taking a dynamic regex string is
        not the right interface.
        """
        # Cache the regex compilation.  This could also be LookAheadFor(THEAD)
        # or something.
        pat = self.cache.get(regex)
        if pat is None:
            pat = re.compile(regex)
            self.cache[regex] = pat

        m = pat.match(self.s, self.pos)
        return m is not None


A_NAME_LEX = [
    # Leading whitespace is required, to separate attributes.
    #
    # If the = is not present, then we set the lexer in a state for
    # attr_value_e.Missing.
    (r'\s+ (%s) \s* (=)? \s*' % _NAME, attr_name.Ok),
    # unexpected EOF

    # The closing > or /> is treated as end of stream, and it's not an error.
    (r'\s* /? >', attr_name.Done),

    # NUL should not be possible, because the top-level

    # This includes < - it is not BadLessThan because it's NOT recoverable
    (r'.', attr_name.Invalid),
]

A_NAME_LEX_COMPILED = MakeLexer(A_NAME_LEX)

# Here we just loop on regular tokens
#
# Examples:
# <a href = unquoted&amp;foo >
# <a href = unquoted&foo >     # BadAmpersand is allowed I guess
# <a href ="unquoted&foo" >    # double quoted
# <a href ='unquoted&foo' >    # single quoted
# <a href = what"foo" >        # HTML5 allows this, but we could disallow it if
# it's not common.  It opens up the j"" and $"" extensions
# <a href = what'foo' >        # ditto

# TODO: get rid of OLD copy
_UNQUOTED_VALUE_OLD = r'''[^ \t\r\n<>&"'\x00]*'''
_UNQUOTED_VALUE = r'''[^ \t\r\n<>&"'\x00]+'''

# What comes after = ?
A_VALUE_LEX = [
    (r'"', h8_val_id.DoubleQuote),
    (r"'", h8_val_id.SingleQuote),
    (_UNQUOTED_VALUE, h8_val_id.UnquotedVal),
    (r'.', h8_val_id.NoMatch),
]

A_VALUE_LEX_COMPILED = MakeLexer(A_VALUE_LEX)

# What's inside "" or '' ?
QUOTED_VALUE_LEX = CHAR_LEX + [
    (r'"', h8_id.DoubleQuote),
    (r"'", h8_id.SingleQuote),
    (r'<', h8_id.BadLessThan),  # BadAmpersand is in CharLex

    # TODO: think about whitespace for efficient class= queries?
    #(r'[ \r\n\t]', h8_id.Whitespace),  # terminates unquoted values
    (r'''[^"'<>&\x00]+''', h8_id.RawData),
    # This includes > - it is not BadGreaterThan because it's NOT recoverable
    (r'.', h8_id.Invalid),
]

QUOTED_VALUE_LEX_COMPILED = MakeLexer(QUOTED_VALUE_LEX)


class AttrLexer(object):
    """
    Typical usage:

    while True:
        n, start_pos, end_pos = attr_lx.ReadName()
        if n == attr_name.Ok:
            if attr_lx.AttrNameEquals('div'):
              print('div')

            # TODO: also pass Optional[List[]] out_tokens?
            v, start_pos, end_pos = attr_lx.ReadValue()
    """

    def __init__(self, s):
        # type: (str) -> None
        self.s = s

        self.tok_id = h8_id.Invalid  # Uninitialized
        self.tag_name_pos = -1  # Invalid
        self.tag_end_pos = -1
        self.must_not_exceed_pos = -1

        self.pos = -1

        self.name_start = -1
        self.name_end = -1
        self.next_value_is_missing = False

        self.init_t = -1
        self.init_e = -1

    def Init(self, tok_id, tag_name_pos, end_pos):
        # type: (h8_id_t, int, int) -> None
        """Initialize so we can read names and values.

        Example:
          'x <a y>'  # tag_name_pos=4, end_pos=6
          'x <a>'    # tag_name_pos=4, end_pos=4

        The Init() method is used to reuse instances of the AttrLexer object.
        """
        assert tag_name_pos >= 0, tag_name_pos
        assert end_pos >= 0, end_pos

        #log('TAG NAME POS %d', tag_name_pos)

        self.tok_id = tok_id
        self.tag_name_pos = tag_name_pos
        self.end_pos = end_pos

        # Check for ambiguous <img src=/>
        if tok_id == h8_id.StartTag:
            self.must_not_exceed_pos = end_pos - 1  # account for >
        elif tok_id == h8_id.StartEndTag:
            self.must_not_exceed_pos = end_pos - 2  # account for />
        else:
            raise AssertionError(tok_id)

        self.pos = tag_name_pos

        # For Reset()
        self.init_t = tag_name_pos
        self.init_e = end_pos

    def Reset(self):
        # type: () -> None

        # TODO: maybe GetAttrRaw() should call this directly?  But not any of
        # the AllAttrs() methods?
        self.tag_name_pos = self.init_t
        self.end_pos = self.init_e
        self.pos = self.init_t

    def ReadName(self):
        # type: () -> Tuple[attr_name_t, int, int]
        """Reads the attribute name

        EOF case: 
          <a>
          <a >

        Error case:
          <a !>
          <a foo=bar !>
        """
        for pat, a in A_NAME_LEX_COMPILED:
            m = pat.match(self.s, self.pos)
            #log('ReadName() matching %r at %d', self.s, self.pos)
            if m:
                #log('ReadName() tag_name_pos %d pos, %d %s', self.tag_name_pos, self.pos, m.groups())
                if a == attr_name.Invalid:
                    #log('m.groups %s', m.groups())
                    return attr_name.Invalid, -1, -1

                self.pos = m.end(0)  # Advance if it's not invalid

                if a == attr_name.Ok:
                    #log('%r', m.groups())
                    self.name_start = m.start(1)
                    self.name_end = m.end(1)
                    # Is the equals sign missing?  Set state.
                    if m.group(2) is None:
                        self.next_value_is_missing = True
                        # HACK: REWIND, since we don't want to consume whitespace
                        self.pos = self.name_end
                    else:
                        self.next_value_is_missing = False
                    return attr_name.Ok, self.name_start, self.name_end
                else:
                    # Reset state - e.g. you must call AttrNameEquals
                    self.name_start = -1
                    self.name_end = -1

                if a == attr_name.Done:
                    return attr_name.Done, -1, -1
        else:
            context = self.s[self.pos:]
            #log('s %r %d', self.s, self.pos)
            raise AssertionError('h8_id.Invalid rule should have matched %r' %
                                 context)

    def _CanonicalAttrName(self):
        # type: () -> str
        """Return the lower case attribute name.

        Must call after ReadName()
        """
        assert self.name_start >= 0, self.name_start
        assert self.name_end >= 0, self.name_end

        attr_name = self.s[self.name_start:self.name_end]
        if attr_name.islower():
            return attr_name
        else:
            return attr_name.lower()

    def AttrNameEquals(self, expected):
        # type: (str) -> bool
        """
        Must call after ReadName()

        TODO: This can be optimized to be "in place", with zero allocs.
        """
        return expected == self._CanonicalAttrName()

    def _QuotedRead(self):
        # type: () -> Tuple[h8_id_t, int]

        for pat, tok_id in QUOTED_VALUE_LEX_COMPILED:
            m = pat.match(self.s, self.pos)
            if m:
                end_pos = m.end(0)  # Advance
                #log('_QuotedRead %r', self.s[self.pos:end_pos])
                return tok_id, end_pos
        else:
            context = self.s[self.pos:self.pos + 10]
            raise AssertionError('h8_id.Invalid rule should have matched %r' %
                                 context)

    def ReadValue(self, tokens_out=None):
        # type: (Optional[List[Tuple[h8_id, int]]]) -> Tuple[attr_value_t, int, int]
        """Read the attribute value.

        In general, it is escaped or "raw"

        Can only be called after a SUCCESSFUL ReadName().
        Assuming ReadName() returned a value, this should NOT fail.
        """
        # ReadName() invariant
        assert self.name_start >= 0, self.name_start
        assert self.name_end >= 0, self.name_end

        self.name_start = -1
        self.name_end = -1

        if self.next_value_is_missing:
            # Do not advance self.pos
            #log('-> MISSING pos %d : %r', self.pos, self.s[self.pos:])
            return attr_value_e.Missing, -1, -1

        # Now read " ', unquoted or empty= is valid too.
        for pat, a in A_VALUE_LEX_COMPILED:
            m = pat.match(self.s, self.pos)
            if m:
                first_end_pos = m.end(0)
                # We shouldn't go past the end
                assert first_end_pos <= self.end_pos, \
                        'first_end_pos = %d should be less than self.end_pos = %d' % (first_end_pos, self.end_pos)
                #log('m %s', m.groups())

                # Note: Unquoted value can't contain &amp; etc. now, so there
                # is no unquoting, and no respecting tokens_raw.
                if a == h8_val_id.UnquotedVal:
                    if first_end_pos > self.must_not_exceed_pos:
                        #log('first_end_pos %d', first_end_pos)
                        #log('must_not_exceed_pos %d', self.must_not_exceed_pos)
                        raise LexError(
                            'Ambiguous slash: last attribute should be quoted',
                            self.s, first_end_pos)
                    self.pos = first_end_pos  # Advance
                    return attr_value_e.Unquoted, m.start(0), first_end_pos

                # TODO: respect tokens_out
                if a == h8_val_id.DoubleQuote:
                    self.pos = first_end_pos
                    while True:
                        tok_id, q_end_pos = self._QuotedRead()
                        #log('self.pos %d q_end_pos %d', self.pos, q_end_pos)
                        if tok_id == h8_id.Invalid:
                            raise LexError(
                                'ReadValue() got invalid token (DQ)', self.s,
                                self.pos)
                        if tok_id == h8_id.DoubleQuote:
                            right_pos = self.pos
                            self.pos = q_end_pos  # Advance past "
                            return attr_value_e.DoubleQuoted, first_end_pos, right_pos
                        self.pos = q_end_pos  # Advance _QuotedRead

                # TODO: respect tokens_out
                if a == h8_val_id.SingleQuote:
                    self.pos = first_end_pos
                    while True:
                        tok_id, q_end_pos = self._QuotedRead()
                        if tok_id == h8_id.Invalid:
                            raise LexError(
                                'ReadValue() got invalid token (SQ)', self.s,
                                self.pos)
                        if tok_id == h8_id.SingleQuote:
                            right_pos = self.pos
                            self.pos = q_end_pos  # Advance past "
                            return attr_value_e.SingleQuoted, first_end_pos, right_pos
                        self.pos = q_end_pos  # Advance _QuotedRead

                if a == h8_val_id.NoMatch:
                    # <a foo = >
                    return attr_value_e.Empty, -1, -1
        else:
            raise AssertionError('h8_val_id.NoMatch rule should have matched')


def GetAttrRaw(attr_lx, name):
    # type: (AttrLexer, str) -> Optional[str]
    while True:
        n, name_start, name_end = attr_lx.ReadName()
        #log('==> ReadName %s %d %d', attr_name_str(n), name_start, name_end)
        if n == attr_name.Ok:
            if attr_lx.AttrNameEquals(name):
                v, val_start, val_end = attr_lx.ReadValue()
                return attr_lx.s[val_start:val_end]
            else:
                # Problem with stateful API: You are forced to either ReadValue()
                # or SkipVlaue()
                attr_lx.ReadValue()
        elif n == attr_name.Done:
            break
        elif n == attr_name.Invalid:
            raise LexError('GetAttrRaw() got invalid token', attr_lx.s,
                           attr_lx.pos)
        else:
            raise AssertionError()

    return None


def AllAttrsRawSlice(attr_lx):
    # type: (AttrLexer) -> List[Tuple[int, int, attr_value_t, int, int]]
    result = []
    while True:
        n, name_start, name_end = attr_lx.ReadName()
        if 0:
            log('  AllAttrsRaw ==> ReadName %s %d %d %r', attr_name_str(n),
                name_start, name_end, attr_lx.s[attr_lx.pos:attr_lx.pos + 10])
        if n == attr_name.Ok:
            #name = attr_lx.s[name_start:name_end]
            #log('  Name %r', name)

            v, val_start, val_end = attr_lx.ReadValue()
            #val = attr_lx.s[val_start:val_end]
            #log('  ReadValue %r', val)
            result.append((name_start, name_end, v, val_start, val_end))
        elif n == attr_name.Done:
            break
        elif n == attr_name.Invalid:
            raise LexError('AllAttrsRaw() got invalid token', attr_lx.s,
                           attr_lx.pos)
        else:
            raise AssertionError()

    return result


def AllAttrsRaw(attr_lx):
    # type: (AttrLexer) -> List[Tuple[str, str]]
    """
    Get a list of pairs [('class', 'foo'), ('href', '?foo=1&amp;bar=2')]

    The quoted values may be escaped.  We would need another lexer to
    unescape them.
    """
    slices = AllAttrsRawSlice(attr_lx)
    pairs = []
    s = attr_lx.s
    for name_start, name_end, val_id, val_start, val_end in slices:
        n = s[name_start:name_end]
        v = s[val_start:val_end]
        pairs.append((n, v))
    return pairs


#
# OLD API - REMOVE THIS
#

# Tag names:
#   Match <a  or </a
#   Match <h2, but not <2h
#
# HTML 5 doesn't restrict tag names at all
#   https://html.spec.whatwg.org/#toc-syntax
#
# XML allows : - .
#  https://www.w3.org/TR/xml/#NT-NameChar

# Namespaces for MathML, SVG
# XLink, XML, XMLNS
#
# https://infra.spec.whatwg.org/#namespaces
#
# Allow - for td-attrs

# TODO: we don't need to capture the tag name here?  That's done at the top
# level
_TAG_RE = re.compile(r'/? \s* (%s)' % _NAME, re.VERBOSE)

_TAG_LAST_RE = re.compile(r'\s* /? >', re.VERBOSE)

# To match href="foo"
# Note: in HTML5 and XML, single quoted attributes are also valid

# <button disabled> is standard usage

# NOTE: This used to allow whitespace around =
# <a foo = "bar">  makes sense in XML
# But then you also have
# <a foo= bar> - which is TWO attributes, in HTML5
# So the space is problematic

_ATTR_RE = re.compile(
    r'''
\s+                     # Leading whitespace is required
(%s)                    # Attribute name
(?:                     # Optional attribute value
  \s* = \s*             # Spaces allowed around =
  (?:
    " ([^>"\x00]*) "    # double quoted value
  | ' ([^>'\x00]*) '    # single quoted value
  | (%s)                # Attribute value
  )
)?             
''' % (_NAME, _UNQUOTED_VALUE_OLD), re.VERBOSE)


class TagLexer(object):
    """
    Given a tag like <a href="..."> or <link type="..." />, the TagLexer
    provides a few operations:

    - What is the tag?
    - Iterate through the attributes, giving (name, value_start_pos, value_end_pos)
    """

    def __init__(self, s):
        # type: (str) -> None
        self.s = s
        self.start_pos = -1  # Invalid
        self.end_pos = -1

    def Reset(self, start_pos, end_pos):
        # type: (int, int) -> None
        """Reuse instances of this object."""
        assert start_pos >= 0, start_pos
        assert end_pos >= 0, end_pos

        self.start_pos = start_pos
        self.end_pos = end_pos

    def WholeTagString(self):
        # type: () -> str
        """Return the entire tag string, e.g. <a href='foo'>"""
        return self.s[self.start_pos:self.end_pos]

    def GetTagName(self):
        # type: () -> str
        # First event
        tok_id, start, end = next(self.Tokens())
        return self.s[start:end]

    def GetSpanForAttrValue(self, attr_name):
        # type: (str) -> Tuple[int, int]
        """
        Used by oils_doc.py, for href shortcuts
        """
        # Algorithm: search for QuotedValue or UnquotedValue after AttrName
        # TODO: Could also cache these

        events = self.Tokens()
        val = (-1, -1)
        try:
            while True:
                tok_id, start, end = next(events)
                if tok_id == h8_tag_id.AttrName:
                    name = self.s[start:end]
                    if name == attr_name:
                        # The value should come next
                        tok_id, start, end = next(events)
                        assert tok_id in (
                            h8_tag_id.QuotedValue, h8_tag_id.UnquotedValue,
                            h8_tag_id.MissingValue), h8_tag_id_str(tok_id)
                        val = start, end
                        break

        except StopIteration:
            pass
        return val

    def GetAttrRaw(self, attr_name):
        # type: (str) -> Optional[str]
        """
        Return the value, which may be UNESCAPED.
        """
        start, end = self.GetSpanForAttrValue(attr_name)
        if start == -1:
            return None
        return self.s[start:end]

    def AllAttrsRawSlice(self):
        # type: () -> List[Tuple[str, int, int]]
        """
        Get a list of pairs [('class', 3, 5), ('href', 9, 12)]
        """
        slices = []
        events = self.Tokens()
        try:
            while True:
                tok_id, start, end = next(events)
                if tok_id == h8_tag_id.AttrName:
                    name = self.s[start:end]

                    # The value should come next
                    tok_id, start, end = next(events)
                    assert tok_id in (
                        h8_tag_id.QuotedValue, h8_tag_id.UnquotedValue,
                        h8_tag_id.MissingValue), h8_tag_id_str(tok_id)
                    # Note: quoted values may have &amp;
                    # We would need ANOTHER lexer to unescape them, but we
                    # don't need that for ul-table
                    slices.append((name, start, end))
        except StopIteration:
            pass
        return slices

    def AllAttrsRaw(self):
        # type: () -> List[Tuple[str, str]]
        """
        Get a list of pairs [('class', 'foo'), ('href', '?foo=1&amp;bar=2')]

        The quoted values may be escaped.  We would need another lexer to
        unescape them.
        """
        slices = self.AllAttrsRawSlice()
        pairs = []
        for name, start, end in slices:
            pairs.append((name, self.s[start:end]))
        return pairs

    def Tokens(self):
        # type: () -> Iterator[Tuple[h8_tag_id_t, int, int]]
        """
        Yields a sequence of tokens: Tag (AttrName AttrValue?)*

        Where each Token is (Type, start_pos, end_pos)

        Note that start and end are NOT redundant!  We skip over some unwanted
        characters.
        """
        m = _TAG_RE.match(self.s, self.start_pos + 1)
        if not m:
            raise RuntimeError("Couldn't find HTML tag in %r" %
                               self.WholeTagString())
        yield h8_tag_id.TagName, m.start(1), m.end(1)

        pos = m.end(0)
        #log('POS %d', pos)

        while True:
            # don't search past the end
            m = _ATTR_RE.match(self.s, pos, self.end_pos)
            if not m:
                #log('BREAK pos %d', pos)
                break
            #log('AttrName %r', m.group(1))

            yield h8_tag_id.AttrName, m.start(1), m.end(1)

            #log('m.groups() %r', m.groups())
            if m.group(2) is not None:
                # double quoted
                yield h8_tag_id.QuotedValue, m.start(2), m.end(2)
            elif m.group(3) is not None:
                # single quoted - TODO: could have different token types
                yield h8_tag_id.QuotedValue, m.start(3), m.end(3)
            elif m.group(4) is not None:
                yield h8_tag_id.UnquotedValue, m.start(4), m.end(4)
            else:
                # <button disabled>
                end = m.end(0)
                yield h8_tag_id.MissingValue, end, end

            # Skip past the "
            pos = m.end(0)

        #log('TOK %r', self.s)

        m = _TAG_LAST_RE.match(self.s, pos)
        #log('_TAG_LAST_RE match %r', self.s[pos:])
        if not m:
            raise LexError('Extra data at end of tag', self.s, pos)
