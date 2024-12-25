#!/usr/bin/env python2
"""
lazylex/html.py - Low-Level HTML Processing.

See lazylex/README.md for details.

TODO: This should be an Oils library eventually.  It's a "lazily-parsed data
structure" like TSV8
"""
from __future__ import print_function

import cStringIO
import re
import sys

from typing import List, Tuple


def log(msg, *args):
    msg = msg % args
    print(msg, file=sys.stderr)


class LexError(Exception):
    """For bad lexical elements like <> or &&"""

    def __init__(self, s, pos):
        self.s = s
        self.pos = pos

    def __str__(self):
        return '(LexError %r)' % (self.s[self.pos:self.pos + 20])


class ParseError(Exception):
    """For errors in the tag structure."""

    def __init__(self, msg, *args):
        self.msg = msg
        self.args = args

    def __str__(self):
        return '(ParseError %s)' % (self.msg % self.args)


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
TOKENS = 'Decl Comment Processing StartTag StartEndTag EndTag DecChar HexChar CharEntity RawData Invalid EndOfStream'.split(
)


class Tok(object):
    """
    Avoid lint errors by using these aliases
    """
    pass


assert len(TOKENS) == 12, TOKENS

TOKEN_NAMES = [None] * len(TOKENS)  # type: List[str]

this_module = sys.modules[__name__]
for i, tok_str in enumerate(TOKENS):
    setattr(this_module, tok_str, i)
    setattr(Tok, tok_str, i)
    TOKEN_NAMES[i] = tok_str


def TokenName(tok_id):
    return TOKEN_NAMES[tok_id]


def MakeLexer(rules):
    return [
        # DOTALL is for the comment
        (re.compile(pat, re.VERBOSE | re.DOTALL), i) for (pat, i) in rules
    ]


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

LEXER = [
    # TODO: instead of nongreedy matches, the loop can just do .find('-->') and
    # .find('?>')

    # Actually non-greedy matches are regular and can be matched in linear time
    # with RE2.
    #
    # https://news.ycombinator.com/item?id=27099798
    #
    # Maybe try combining all of these for speed.
    (r'<!-- .*? -->', Tok.Comment),
    (r'<\? .*? \?>', Tok.Processing),

    # NOTE: < is allowed in these.
    (r'<! [^>]+ >', Tok.Decl),  # <!DOCTYPE html>
    (r'</ [^>]+ >', Tok.EndTag),  # self-closing <br/>  comes FIRST
    (r'< [^>]+ />', Tok.StartEndTag),  # end </a>
    (r'< [^>]+  >', Tok.StartTag),  # start <a>
    (r'&\# [0-9]+ ;', Tok.DecChar),
    (r'&\# x[0-9a-fA-F]+ ;', Tok.HexChar),
    (r'& [a-zA-Z]+ ;', Tok.CharEntity),

    # Note: > is allowed in raw data.
    # https://stackoverflow.com/questions/10462348/right-angle-bracket-in-html
    (r'[^&<]+', Tok.RawData),
    (r'.', Tok.Invalid),  # error!
]

LEXER = MakeLexer(LEXER)


class Lexer(object):

    def __init__(self, s, left_pos=0, right_pos=-1):
        self.s = s
        self.pos = left_pos
        self.right_pos = len(s) if right_pos == -1 else right_pos

    def _Peek(self):
        # type: () -> Tuple[int, int]
        if self.pos == self.right_pos:
            return Tok.EndOfStream, self.pos

        assert self.pos < self.right_pos, self.pos

        # Find the first match.
        # Note: frontend/match.py uses _LongestMatch(), which is different!
        # TODO: reconcile them.  This lexer should be expressible in re2c.
        for pat, tok_id in LEXER:
            m = pat.match(self.s, self.pos)
            if m:
                return tok_id, m.end()
        else:
            raise AssertionError('Tok.Invalid rule should have matched')

    def Read(self):
        # type: () -> Tuple[int, int]
        tok_id, end_pos = self._Peek()
        self.pos = end_pos  # advance
        return tok_id, end_pos

    def LookAhead(self, regex):
        # TODO: test if it matches the regex.  Don't need Peek()
        return True


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

_TAG_RE = re.compile(r'/? \s* ([a-zA-Z][a-zA-Z0-9-]*)', re.VERBOSE)

# To match href="foo"

_ATTR_RE = re.compile(
    r'''
\s+                     # Leading whitespace is required
([a-z]+)                # Attribute name
(?:                     # Optional attribute value
  \s* = \s*
  (?:
    " ([^>"]*) "        # double quoted value
  | ([a-zA-Z0-9_\-]+)   # Just allow unquoted "identifiers"
                        # TODO: relax this?  for href=$foo
  )
)?             
''', re.VERBOSE)

TagName, AttrName, UnquotedValue, QuotedValue = range(4)


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
        self.start_pos = start_pos
        self.end_pos = end_pos

    def TagString(self):
        return self.s[self.start_pos:self.end_pos]

    def TagName(self):
        # First event
        tok_id, start, end = next(self.Tokens())
        return self.s[start:end]

    def GetSpanForAttrValue(self, attr_name):
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
                        if tok_id in (QuotedValue, UnquotedValue):
                            # Note: quoted values may have &amp;
                            # We would need ANOTHER lexer to unescape them.
                            # Right now help_gen.py and oils_doc.py
                            val = start, end
                            break

        except StopIteration:
            pass
        return val

    def GetAttrRaw(self, attr_name):
        """
        Return the value, which may be UNESCAPED.
        """
        # Algorithm: search for QuotedValue or UnquotedValue after AttrName
        # TODO: Could also cache these
        start, end = self.GetSpanForAttrValue(attr_name)
        if start == -1:
            return None
        return self.s[start:end]

    def AllAttrsRaw(self):
        """
        Get a list of pairs [('class', 'foo'), ('href', '?foo=1&amp;bar=2')]

        The quoted values may be escaped.  We would need another lexer to
        unescape them.
        """
        pairs = []
        events = self.Tokens()
        try:
            while True:
                tok_id, start, end = next(events)
                if tok_id == AttrName:
                    name = self.s[start:end]

                    # The value should come next
                    tok_id, start, end = next(events)
                    if tok_id in (QuotedValue, UnquotedValue):
                        # Note: quoted values may have &amp;
                        # We would need ANOTHER lexer to unescape them, but we
                        # don't need that for ul-table

                        val = self.s[start:end]
                        pairs.append((name, val))
        except StopIteration:
            pass
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

        while True:
            # don't search past the end
            m = _ATTR_RE.match(self.s, pos, self.end_pos)
            if not m:
                # A validating parser would check that > or /> is next -- there's no junk
                break

            yield AttrName, m.start(1), m.end(1)

            # Quoted is group 2, unquoted is group 3.
            if m.group(2) is not None:
                yield QuotedValue, m.start(2), m.end(2)
            elif m.group(3) is not None:
                yield UnquotedValue, m.start(3), m.end(3)

            # Skip past the "
            pos = m.end(0)


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

    raise ParseError('No start tag %r', tag_name)


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

    raise ParseError('No end tag %r', tag_name)


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
      doctool/make_help.py: HelpIndexCards

    In the latter case, we cold process some tags, like:

    - Blue Link (not clickable, but still useful)
    - Red X

    That should be html.ToAnsi.
    """
    f = cStringIO.StringIO()
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
