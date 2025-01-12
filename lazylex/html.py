#!/usr/bin/env python2
"""
lazylex/html.py - Low-Level HTML Processing.

See lazylex/README.md for details.

Conflicts between HTML5 and XML:

- In XML, <source> is like any tag, and must be closed,
- In HTML, <source> is a VOID tag, and must NOT be closedlike any tag, and must be closed,

- In XML, <script> and <style> don't have special treatment
- In HTML, they do

- The header is different - <!DOCTYPE html> vs.  <?xml version= ... ?>

So do have a mode for <script> <style> and void tags?  Upgrade HX8 into HTM8?
"""
from __future__ import print_function

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO  # python3
import re
import sys

if sys.version_info.major == 2:
    from typing import List, Tuple, Optional


def log(msg, *args):
    msg = msg % args
    print(msg, file=sys.stderr)


class LexError(Exception):
    """
    Examples of lex errors:

    - Tok.Invalid, like <> or &&
    - Unclosed <!--  <?  <![CDATA[  <script>  <style>
    """

    def __init__(self, s, start_pos):
        self.s = s
        self.start_pos = start_pos

    def __str__(self):
        return '(LexError %r)' % (self.s[self.start_pos:self.start_pos + 20])


def FindLineNum(s, error_pos):
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
        self.msg = msg
        self.s = s
        self.start_pos = start_pos

    def __str__(self):
        if self.s is not None:
            assert self.start_pos != -1, self.start_pos
            snippet = (self.s[self.start_pos:self.start_pos + 20])

            line_num = FindLineNum(self.s, self.start_pos)
        else:
            snippet = ''
            line_num = -1
        msg = 'line %d: %r %r' % (line_num, self.msg, snippet)
        return msg


class Output(object):
    """Takes an underlying input buffer and an output file.  Maintains a
    position in the input buffer.

    Print FROM the input or print new text to the output.
    """

    def __init__(self, s, f, left_pos=0, right_pos=-1):
        self.s = s
        self.f = f
        self.pos = left_pos
        self.right_pos = len(s) if right_pos == -1 else right_pos

    def SkipTo(self, pos):
        """Skip to a position."""
        self.pos = pos

    def PrintUntil(self, pos):
        """Print until a position."""
        piece = self.s[self.pos:pos]
        self.f.write(piece)
        self.pos = pos

    def PrintTheRest(self):
        """Print until the end of the string."""
        self.PrintUntil(self.right_pos)

    def Print(self, s):
        """Print text to the underlying buffer."""
        self.f.write(s)


# HTML Tokens
# CommentBegin, ProcessingBegin, CDataBegin are "pseudo-tokens", not visible
TOKENS = 'Decl Comment CommentBegin Processing ProcessingBegin CData CDataBegin StartTag StartEndTag EndTag DecChar HexChar CharEntity RawData HtmlCData Invalid EndOfStream'.split(
)


class Tok(object):
    """
    Avoid lint errors by using these aliases
    """
    pass


TOKEN_NAMES = [None] * len(TOKENS)  # type: List[str]

this_module = sys.modules[__name__]
for i, tok_str in enumerate(TOKENS):
    setattr(this_module, tok_str, i)
    setattr(Tok, tok_str, i)
    TOKEN_NAMES[i] = tok_str


def TokenName(tok_id):
    return TOKEN_NAMES[tok_id]


def MakeLexer(rules):
    return [(re.compile(pat, re.VERBOSE), i) for (pat, i) in rules]


#
# Eggex
#
# Tag      = / ~['>']+ /

# Is this valid?  A single character?
# Tag      = / ~'>'* /

# Maybe better: / [NOT '>']+/
# capital letters not allowed there?
#
# But then this is confusing:
# / [NOT ~digit]+/
#
# / [NOT digit] / is [^\d]
# / ~digit /      is \D
#
# Or maybe:
#
# / [~ digit]+ /
# / [~ '>']+ /
# / [NOT '>']+ /

# End      = / '</' Tag  '>' /
# StartEnd = / '<'  Tag '/>' /
# Start    = / '<'  Tag  '>' /
#
# EntityRef = / '&' dot{* N} ';' /

# Tag name, or attribute name
# colon is used in XML

# https://www.w3.org/TR/xml/#NT-Name
# Hm there is a lot of unicode stuff.  We are simplifying parsing

_NAME = r'[a-zA-Z][a-zA-Z0-9:_\-]*'  # must start with letter

CHAR_LEX = [
    # Characters
    # https://www.w3.org/TR/xml/#sec-references
    (r'&\# [0-9]+ ;', Tok.DecChar),
    (r'&\# x[0-9a-fA-F]+ ;', Tok.HexChar),
    (r'& %s ;' % _NAME, Tok.CharEntity),
]

LEXER = CHAR_LEX + [
    (r'<!--', Tok.CommentBegin),

    # Processing instruction are used for the XML header:
    # <?xml version="1.0" encoding="UTF-8"?>
    # They are technically XML-only, but in HTML5, they are another kind of
    # comment:
    #
    #   https://developer.mozilla.org/en-US/docs/Web/API/ProcessingInstruction
    #
    (r'<\?', Tok.ProcessingBegin),
    # Not necessary in HTML5, but occurs in XML
    (r'<!\[CDATA\[', Tok.CDataBegin),  # <![CDATA[

    # Markup declarations
    # - In HTML5, there is only <!DOCTYPE html>
    # - XML has 4 more declarations: <!ELEMENT ...> ATTLIST ENTITY NOTATION
    #   - these seem to be part of DTD
    #   - it's useful to skip these, and be able to parse the rest of the document
    # - Note: < is allowed?
    (r'<! [^>\x00]+ >', Tok.Decl),

    # Tags
    # Notes:
    # - We look for a valid tag name, but we don't validate attributes.
    #   That's done in the tag lexer.
    # - We don't allow leading whitespace
    (r'</ (%s) >' % _NAME, Tok.EndTag),
    # self-closing <br/>  comes before StartTag
    # could/should these be collapsed into one rule?
    (r'<  (%s) [^>\x00]* />' % _NAME, Tok.StartEndTag),  # end </a>
    (r'<  (%s) [^>\x00]* >' % _NAME, Tok.StartTag),  # start <a>

    # HTML5 allows unescaped > in raw data, but < is not allowed.
    # https://stackoverflow.com/questions/10462348/right-angle-bracket-in-html
    #
    # - My early blog has THREE errors when disallowing >
    # - So do some .wwz files
    (r'[^&<\x00]+', Tok.RawData),
    (r'.', Tok.Invalid),  # error!
]

#  Old notes:
#
# Non-greedy matches are regular and can be matched in linear time
# with RE2.
#
# https://news.ycombinator.com/item?id=27099798
#
# Maybe try combining all of these for speed.

# . is any char except newline
# https://re2c.org/manual/manual_c.html

# Discarded options
#(r'<!-- .*? -->', Tok.Comment),

# Hack from Claude: \s\S instead of re.DOTALL.  I don't like this
#(r'<!-- [\s\S]*? -->', Tok.Comment),
#(r'<!-- (?:.|[\n])*? -->', Tok.Comment),

LEXER = MakeLexer(LEXER)


class Lexer(object):

    def __init__(self, s, left_pos=0, right_pos=-1, no_special_tags=False):
        self.s = s
        self.pos = left_pos
        self.right_pos = len(s) if right_pos == -1 else right_pos
        self.no_special_tags = no_special_tags

        self.cache = {}  # string -> compiled regex pattern object

        # either </script> or </style> - we search until we see that
        self.search_state = None  # type: Optional[str]

        # Position of tag name, if applicable
        # - Set after you get a StartTag, EndTag, or StartEndTag
        # - Unset on other tags
        self.tag_pos_left = -1
        self.tag_pos_right = -1

    def _Peek(self):
        # type: () -> Tuple[int, int]
        """
        Note: not using _Peek() now
        """
        if self.pos == self.right_pos:
            return Tok.EndOfStream, self.pos

        assert self.pos < self.right_pos, self.pos

        if self.search_state is not None and not self.no_special_tags:
            pos = self.s.find(self.search_state, self.pos)
            if pos == -1:
                # unterminated <script> or <style>
                raise LexError(self.s, self.pos)
            self.search_state = None
            # beginning
            return Tok.HtmlCData, pos

        # Find the first match.
        # Note: frontend/match.py uses _LongestMatch(), which is different!
        # TODO: reconcile them.  This lexer should be expressible in re2c.

        for pat, tok_id in LEXER:
            m = pat.match(self.s, self.pos)
            if m:
                if tok_id in (Tok.StartTag, Tok.EndTag, Tok.StartEndTag):
                    self.tag_pos_left = m.start(1)
                    self.tag_pos_right = m.end(1)
                else:
                    # Reset state
                    self.tag_pos_left = -1
                    self.tag_pos_right = -1

                if tok_id == Tok.CommentBegin:
                    pos = self.s.find('-->', self.pos)
                    if pos == -1:
                        # unterminated <!--
                        raise LexError(self.s, self.pos)
                    return Tok.Comment, pos + 3  # -->

                if tok_id == Tok.ProcessingBegin:
                    pos = self.s.find('?>', self.pos)
                    if pos == -1:
                        # unterminated <?
                        raise LexError(self.s, self.pos)
                    return Tok.Processing, pos + 2  # ?>

                if tok_id == Tok.CDataBegin:
                    pos = self.s.find(']]>', self.pos)
                    if pos == -1:
                        # unterminated <![CDATA[
                        raise LexError(self.s, self.pos)
                    return Tok.CData, pos + 3  # ]]>

                if tok_id == Tok.StartTag:
                    if self.TagNameEquals('script'):
                        self.search_state = '</script>'
                    elif self.TagNameEquals('style'):
                        self.search_state = '</style>'

                return tok_id, m.end()
        else:
            raise AssertionError('Tok.Invalid rule should have matched')

    def TagNameEquals(self, expected):
        # type: (str) -> bool
        assert self.tag_pos_left != -1, self.tag_pos_left
        assert self.tag_pos_right != -1, self.tag_pos_right

        # TODO: In C++, this does not need an allocation
        # TODO: conditionally lower() case here (maybe not in XML mode)
        return expected == self.s[self.tag_pos_left:self.tag_pos_right]

    def TagName(self):
        # type: () -> None
        assert self.tag_pos_left != -1, self.tag_pos_left
        assert self.tag_pos_right != -1, self.tag_pos_right

        # TODO: conditionally lower() case here (maybe not in XML mode)
        return self.s[self.tag_pos_left:self.tag_pos_right]

    def Read(self):
        # type: () -> Tuple[int, int]
        tok_id, end_pos = self._Peek()
        self.pos = end_pos  # advance
        return tok_id, end_pos

    def LookAhead(self, regex):
        # Cache the regex compilation.  This could also be LookAheadFor(THEAD)
        # or something.
        pat = self.cache.get(regex)
        if pat is None:
            pat = re.compile(regex)
            self.cache[regex] = pat

        m = pat.match(self.s, self.pos)
        return m is not None


def _Tokens(s, left_pos, right_pos):
    """
    Args:
      s: string to parse
      left_pos, right_pos: Optional span boundaries.
    """
    lx = Lexer(s, left_pos, right_pos)
    while True:
        tok_id, pos = lx.Read()
        yield tok_id, pos
        if tok_id == Tok.EndOfStream:
            break


def ValidTokens(s, left_pos=0, right_pos=-1):
    """Wrapper around _Tokens to prevent callers from having to handle Invalid.

    I'm not combining the two functions because I might want to do a
    'yield' transformation on Tokens()?  Exceptions might complicate the
    issue?
    """
    pos = left_pos
    for tok_id, end_pos in _Tokens(s, left_pos, right_pos):
        if tok_id == Tok.Invalid:
            raise LexError(s, pos)
        yield tok_id, end_pos
        pos = end_pos


def ValidTokenList(s, no_special_tags=False):
    """A wrapper that can be more easily translated to C++.  Doesn't use iterators."""

    start_pos = 0
    tokens = []
    lx = Lexer(s, no_special_tags=no_special_tags)
    while True:
        tok_id, end_pos = lx.Read()
        tokens.append((tok_id, end_pos))
        if tok_id == Tok.EndOfStream:
            break
        if tok_id == Tok.Invalid:
            raise LexError(s, start_pos)
        start_pos = end_pos
    return tokens


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

# Be very lenient - just no whitespace or special HTML chars
# I don't think this is more lenient than HTML5, though we should check.
_UNQUOTED_VALUE = r'''[^ \t\r\n<>&"'\x00]*'''

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
  =
  (?:
    " ([^>"\x00]*) "    # double quoted value
  | ' ([^>'\x00]*) '    # single quoted value
  | (%s)                # Attribute value
  )
)?             
''' % (_NAME, _UNQUOTED_VALUE), re.VERBOSE)

TagName, AttrName, UnquotedValue, QuotedValue, MissingValue = range(5)


class TagLexer(object):
    """
    Given a tag like <a href="..."> or <link type="..." />, the TagLexer
    provides a few operations:

    - What is the tag?
    - Iterate through the attributes, giving (name, value_start_pos, value_end_pos)
    """

    def __init__(self, s):
        self.s = s
        self.start_pos = -1  # Invalid
        self.end_pos = -1

    def Reset(self, start_pos, end_pos):
        """Reuse instances of this object."""
        assert start_pos >= 0, start_pos
        assert end_pos >= 0, end_pos

        self.start_pos = start_pos
        self.end_pos = end_pos

    def TagString(self):
        return self.s[self.start_pos:self.end_pos]

    def TagName(self):
        # First event
        tok_id, start, end = next(self.Tokens())
        return self.s[start:end]

    def GetSpanForAttrValue(self, attr_name):
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
                if tok_id == AttrName:
                    name = self.s[start:end]
                    if name == attr_name:
                        # The value should come next
                        tok_id, start, end = next(events)
                        assert tok_id in (QuotedValue, UnquotedValue,
                                          MissingValue), TokenName(tok_id)
                        val = start, end
                        break

        except StopIteration:
            pass
        return val

    def GetAttrRaw(self, attr_name):
        """
        Return the value, which may be UNESCAPED.
        """
        start, end = self.GetSpanForAttrValue(attr_name)
        if start == -1:
            return None
        return self.s[start:end]

    def AllAttrsRawSlice(self):
        """
        Get a list of pairs [('class', 3, 5), ('href', 9, 12)]
        """
        slices = []
        events = self.Tokens()
        try:
            while True:
                tok_id, start, end = next(events)
                if tok_id == AttrName:
                    name = self.s[start:end]

                    # The value should come next
                    tok_id, start, end = next(events)
                    assert tok_id in (QuotedValue, UnquotedValue,
                                      MissingValue), TokenName(tok_id)
                    # Note: quoted values may have &amp;
                    # We would need ANOTHER lexer to unescape them, but we
                    # don't need that for ul-table
                    slices.append((name, start, end))
        except StopIteration:
            pass
        return slices

    def AllAttrsRaw(self):
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
        """
        Yields a sequence of tokens: Tag (AttrName AttrValue?)*

        Where each Token is (Type, start_pos, end_pos)

        Note that start and end are NOT redundant!  We skip over some unwanted
        characters.
        """
        m = _TAG_RE.match(self.s, self.start_pos + 1)
        if not m:
            raise RuntimeError("Couldn't find HTML tag in %r" %
                               self.TagString())
        yield TagName, m.start(1), m.end(1)

        pos = m.end(0)
        #log('POS %d', pos)

        while True:
            # don't search past the end
            m = _ATTR_RE.match(self.s, pos, self.end_pos)
            if not m:
                #log('BREAK pos %d', pos)
                break
            #log('AttrName %r', m.group(1))

            yield AttrName, m.start(1), m.end(1)

            #log('m.groups() %r', m.groups())
            if m.group(2) is not None:
                # double quoted
                yield QuotedValue, m.start(2), m.end(2)
            elif m.group(3) is not None:
                # single quoted - TODO: could have different token types
                yield QuotedValue, m.start(3), m.end(3)
            elif m.group(4) is not None:
                yield UnquotedValue, m.start(4), m.end(4)
            else:
                # <button disabled>
                end = m.end(0)
                yield MissingValue, end, end

            # Skip past the "
            pos = m.end(0)

        #log('TOK %r', self.s)

        m = _TAG_LAST_RE.match(self.s, pos)
        #log('_TAG_LAST_RE match %r', self.s[pos:])
        if not m:
            # Extra data at end of tag.  TODO: add messages for all these.
            raise LexError(self.s, pos)


# This is similar but not identical to
#    " ([^>"\x00]*) "    # double quoted value
#  | ' ([^>'\x00]*) '    # single quoted value
#
# Note: for unquoted values, & isn't allowed, and thus &amp; and &#99; and
# &#x99; are not allowed.  We could relax that?
ATTR_VALUE_LEXER = CHAR_LEX + [
    (r'[^>&\x00]+', Tok.RawData),
    (r'.', Tok.Invalid),
]

ATTR_VALUE_LEXER = MakeLexer(ATTR_VALUE_LEXER)


class AttrValueLexer(object):
    """
    <a href="foo=99&amp;bar">
    <a href='foo=99&amp;bar'>
    <a href=unquoted>
    """

    def __init__(self, s):
        self.s = s
        self.start_pos = -1  # Invalid
        self.end_pos = -1

    def Reset(self, start_pos, end_pos):
        """Reuse instances of this object."""
        assert start_pos >= 0, start_pos
        assert end_pos >= 0, end_pos

        self.start_pos = start_pos
        self.end_pos = end_pos

    def NumTokens(self):
        num_tokens = 0
        pos = self.start_pos
        for tok_id, end_pos in self.Tokens():
            if tok_id == Tok.Invalid:
                raise LexError(self.s, pos)
            pos = end_pos
            #log('pos %d', pos)
            num_tokens += 1
        return num_tokens

    def Tokens(self):
        pos = self.start_pos
        while pos < self.end_pos:
            # Find the first match, like above.
            # Note: frontend/match.py uses _LongestMatch(), which is different!
            # TODO: reconcile them.  This lexer should be expressible in re2c.
            for pat, tok_id in ATTR_VALUE_LEXER:
                m = pat.match(self.s, pos)
                if m:
                    if 0:
                        tok_str = m.group(0)
                        log('token = %r', tok_str)

                    end_pos = m.end(0)
                    yield tok_id, end_pos
                    pos = end_pos
                    break
            else:
                raise AssertionError('Tok.Invalid rule should have matched')


def ReadUntilStartTag(it, tag_lexer, tag_name):
    """Find the next <foo>, returning its (start, end) positions

    Raise ParseError if it's not found.

    tag_lexer is RESET.
    """
    pos = 0
    while True:
        try:
            tok_id, end_pos = next(it)
        except StopIteration:
            break
        tag_lexer.Reset(pos, end_pos)
        if tok_id == Tok.StartTag and tag_lexer.TagName() == tag_name:
            return pos, end_pos

        pos = end_pos

    raise ParseError('No start tag %r' % tag_name)


def ReadUntilEndTag(it, tag_lexer, tag_name):
    """Find the next </foo>, returning its (start, end) position

    Raise ParseError if it's not found.

    tag_lexer is RESET.
    """
    pos = 0
    while True:
        try:
            tok_id, end_pos = next(it)
        except StopIteration:
            break
        tag_lexer.Reset(pos, end_pos)
        if tok_id == Tok.EndTag and tag_lexer.TagName() == tag_name:
            return pos, end_pos

        pos = end_pos

    raise ParseError('No end tag %r' % tag_name)


CHAR_ENTITY = {
    'amp': '&',
    'lt': '<',
    'gt': '>',
    'quot': '"',
}


def ToText(s, left_pos=0, right_pos=-1):
    """Given HTML, return text by unquoting &gt; and &lt; etc.

    Used by:
      doctools/oils_doc.py: PygmentsPlugin
      doctools/help_gen.py: HelpIndexCards

    In the latter case, we cold process some tags, like:

    - Blue Link (not clickable, but still useful)
    - Red X

    That should be html.ToAnsi.
    """
    f = StringIO()
    out = Output(s, f, left_pos, right_pos)

    pos = left_pos
    for tok_id, end_pos in ValidTokens(s, left_pos, right_pos):
        if tok_id == Tok.RawData:
            out.SkipTo(pos)
            out.PrintUntil(end_pos)

        elif tok_id == Tok.CharEntity:  # &amp;

            entity = s[pos + 1:end_pos - 1]

            out.SkipTo(pos)
            out.Print(CHAR_ENTITY[entity])
            out.SkipTo(end_pos)

        # Not handling these yet
        elif tok_id == Tok.HexChar:
            raise AssertionError('Hex Char %r' % s[pos:pos + 20])

        elif tok_id == Tok.DecChar:
            raise AssertionError('Dec Char %r' % s[pos:pos + 20])

        pos = end_pos

    out.PrintTheRest()
    return f.getvalue()


# https://developer.mozilla.org/en-US/docs/Glossary/Void_element
VOID_ELEMENTS = [
    'area',
    'base',
    'br',
    'col',
    'embed',
    'hr',
    'img',
    'input',
    'link',
    'meta',
    'param',
    'source',
    'track',
    'wbr',
]

LEX_ATTRS = 1 << 1
LEX_QUOTED_VALUES = 1 << 2  # href="?x=42&amp;y=99"
NO_SPECIAL_TAGS = 1 << 3  # <script> <style>, VOID tags, etc.
BALANCED_TAGS = 1 << 4  # are tags balanced?


def Validate(contents, flags, counters):
    # type: (str, int, Counters) -> None

    tag_lexer = TagLexer(contents)
    val_lexer = AttrValueLexer(contents)

    no_special_tags = bool(flags & NO_SPECIAL_TAGS)
    lx = Lexer(contents, no_special_tags=no_special_tags)
    tokens = []
    start_pos = 0
    tag_stack = []
    while True:
        tok_id, end_pos = lx.Read()
        #log('TOP %s %r', TokenName(tok_id), contents[start_pos:end_pos])

        if tok_id == Tok.Invalid:
            raise LexError(contents, start_pos)
        if tok_id == Tok.EndOfStream:
            break

        tokens.append((tok_id, end_pos))

        if tok_id == Tok.StartEndTag:
            counters.num_start_end_tags += 1

            tag_lexer.Reset(start_pos, end_pos)
            all_attrs = tag_lexer.AllAttrsRawSlice()
            counters.num_attrs += len(all_attrs)
            for name, val_start, val_end in all_attrs:
                val_lexer.Reset(val_start, val_end)
                counters.num_val_tokens += val_lexer.NumTokens()

            counters.debug_attrs.extend(all_attrs)

        elif tok_id == Tok.StartTag:
            counters.num_start_tags += 1

            tag_lexer.Reset(start_pos, end_pos)
            all_attrs = tag_lexer.AllAttrsRawSlice()
            counters.num_attrs += len(all_attrs)
            for name, val_start, val_end in all_attrs:
                val_lexer.Reset(val_start, val_end)
                counters.num_val_tokens += val_lexer.NumTokens()

            counters.debug_attrs.extend(all_attrs)

            if flags & BALANCED_TAGS:
                tag_name = lx.TagName()
                if flags & NO_SPECIAL_TAGS:
                    tag_stack.append(tag_name)
                else:
                    # e.g. <meta> is considered self-closing, like <meta/>
                    if tag_name not in VOID_ELEMENTS:
                        tag_stack.append(tag_name)

            counters.max_tag_stack = max(counters.max_tag_stack,
                                         len(tag_stack))
        elif tok_id == Tok.EndTag:
            if flags & BALANCED_TAGS:
                try:
                    expected = tag_stack.pop()
                except IndexError:
                    raise ParseError('Tag stack empty',
                                     s=contents,
                                     start_pos=start_pos)

                actual = lx.TagName()
                if expected != actual:
                    raise ParseError(
                        'Got unexpected closing tag %r; opening tag was %r' %
                        (contents[start_pos:end_pos], expected),
                        s=contents,
                        start_pos=start_pos)

        start_pos = end_pos

    if len(tag_stack) != 0:
        raise ParseError('Missing closing tags at end of doc: %s' %
                         ' '.join(tag_stack),
                         s=contents,
                         start_pos=start_pos)

    counters.num_tokens += len(tokens)


class Counters(object):

    def __init__(self):
        self.num_tokens = 0
        self.num_start_tags = 0
        self.num_start_end_tags = 0
        self.num_attrs = 0
        self.max_tag_stack = 0
        self.num_val_tokens = 0

        self.debug_attrs = []


def main(argv):
    action = argv[1]

    if action == 'tokens':
        contents = sys.stdin.read()

        lx = Lexer(contents)
        start_pos = 0
        while True:
            tok_id, end_pos = lx.Read()
            if tok_id == Tok.Invalid:
                raise LexError(contents, start_pos)
            if tok_id == Tok.EndOfStream:
                break

            frag = contents[start_pos:end_pos]
            log('%d %s %r', end_pos, TokenName(tok_id), frag)
            start_pos = end_pos

        return 0

    elif action in ('lex-htm8', 'parse-htm8', 'parse-xml'):

        errors = []
        counters = Counters()

        flags = LEX_ATTRS | LEX_QUOTED_VALUES
        if action.startswith('parse-'):
            flags |= BALANCED_TAGS
        if action == 'parse-xml':
            flags |= NO_SPECIAL_TAGS

        i = 0
        for line in sys.stdin:
            filename = line.strip()
            with open(filename) as f:
                contents = f.read()

            try:
                Validate(contents, flags, counters)
            except LexError as e:
                log('Lex error in %r: %s', filename, e)
                errors.append((filename, e))
            except ParseError as e:
                log('Parse error in %r: %s', filename, e)
                errors.append((filename, e))
            i += 1

        log('')
        log('%10d tokens', counters.num_tokens)
        log('%10d start/end tags', counters.num_start_end_tags)
        log('%10d start tags', counters.num_start_tags)
        log('%10d attrs', counters.num_attrs)
        log('%10d max tag stack depth', counters.max_tag_stack)
        log('%10d attr val tokens', counters.num_val_tokens)
        log('%10d errors', len(errors))
        if len(errors):
            return 1
        return 0

    elif action == 'todo':
        # Other algorithms:
        #
        # - select first subtree with given ID
        #   - this requires understanding the void tags I suppose
        # - select all subtrees that have a class
        # - materialize DOM

        # Safe-HTM8?  This is a filter
        return 0

    else:
        raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
