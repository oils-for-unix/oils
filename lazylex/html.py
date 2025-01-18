#!/usr/bin/env python2
"""
lazylex/html.py - Wrapper around HTM8

See doc/lazylex.md for details.

"""
from __future__ import print_function

import re

from _devbuild.gen.htm8_asdl import (h8_id, h8_id_t, h8_id_str, h8_tag_id,
                                     h8_tag_id_t, h8_tag_id_str)
from data_lang import htm8
from data_lang.htm8 import (Lexer, LexError, ParseError, Output, _NAME_RE)
from doctools.util import log

try:
    from cStringIO import StringIO
except ImportError:
    # for python3
    from io import StringIO  # type: ignore
import sys

if sys.version_info.major == 2:
    from typing import List, Tuple, Iterator, Optional


def _Tokens(s, left_pos, right_pos):
    # type: (str, int, int) -> Iterator[Tuple[h8_id_t, int]]
    """
    Args:
      s: string to parse
      left_pos, right_pos: Optional span boundaries.
    """
    lx = Lexer(s, left_pos, right_pos)
    while True:
        tok_id, pos = lx.Read()
        yield tok_id, pos
        if tok_id == h8_id.EndOfStream:
            break


def ValidTokens(s, left_pos=0, right_pos=-1):
    # type: (str, int, int) -> Iterator[Tuple[h8_id_t, int]]
    """Wrapper around _Tokens to prevent callers from having to handle Invalid.

    I'm not combining the two functions because I might want to do a
    'yield' transformation on Tokens()?  Exceptions might complicate the
    issue?
    """
    pos = left_pos
    for tok_id, end_pos in _Tokens(s, left_pos, right_pos):
        if tok_id == h8_id.Invalid:
            raise LexError('ValidTokens() got invalid token', s, pos)
        yield tok_id, end_pos
        pos = end_pos


def ReadUntilStartTag(it, tag_lexer, tag_name):
    # type: (Iterator[Tuple[h8_id_t, int]], TagLexer, str) -> Tuple[int, int]
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
        if tok_id == h8_id.StartTag and tag_lexer.GetTagName() == tag_name:
            return pos, end_pos

        pos = end_pos

    raise ParseError('No start tag %r' % tag_name)


def ReadUntilEndTag(it, tag_lexer, tag_name):
    # type: (Iterator[Tuple[h8_id_t, int]], TagLexer, str) -> Tuple[int, int]
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
        if tok_id == h8_id.EndTag and tag_lexer.GetTagName() == tag_name:
            return pos, end_pos

        pos = end_pos

    raise ParseError('No end tag %r' % tag_name)


CHAR_ENTITY = {
    'amp': '&',
    'lt': '<',
    'gt': '>',
    'quot': '"',
    'apos': "'",
}


def ToText(s, left_pos=0, right_pos=-1):
    # type: (str, int, int) -> str
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
        if tok_id in (h8_id.RawData, h8_id.BadAmpersand, h8_id.BadGreaterThan,
                      h8_id.BadLessThan):
            out.SkipTo(pos)
            out.PrintUntil(end_pos)

        elif tok_id == h8_id.CharEntity:  # &amp;

            entity = s[pos + 1:end_pos - 1]

            out.SkipTo(pos)
            out.Print(CHAR_ENTITY[entity])
            out.SkipTo(end_pos)

        # Not handling these yet
        elif tok_id == h8_id.HexChar:
            raise AssertionError('Hex Char %r' % s[pos:pos + 20])

        elif tok_id == h8_id.DecChar:
            raise AssertionError('Dec Char %r' % s[pos:pos + 20])

        else:
            # Skip everything else
            out.SkipTo(end_pos)

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

    attr_lx = htm8.AttrLexer(contents)

    no_special_tags = bool(flags & NO_SPECIAL_TAGS)
    lx = htm8.Lexer(contents, no_special_tags=no_special_tags)
    tokens = []
    start_pos = 0
    tag_stack = []
    while True:
        tok_id, end_pos = lx.Read()
        #log('TOP %s %r', h8_id_str(tok_id), contents[start_pos:end_pos])

        if tok_id == h8_id.Invalid:
            raise LexError('Validate() got invalid token', contents, start_pos)
        if tok_id == h8_id.EndOfStream:
            break

        tokens.append((tok_id, end_pos))

        if tok_id == h8_id.StartEndTag:
            counters.num_start_end_tags += 1

            attr_lx.Init(tok_id, lx.TagNamePos(), end_pos)
            all_attrs = htm8.AllAttrsRaw(attr_lx)
            counters.num_attrs += len(all_attrs)
            # TODO: val_lexer.NumTokens() can be replaced with tokens_out

        elif tok_id == h8_id.StartTag:
            counters.num_start_tags += 1

            attr_lx.Init(tok_id, lx.TagNamePos(), end_pos)
            all_attrs = htm8.AllAttrsRaw(attr_lx)
            counters.num_attrs += len(all_attrs)

            #counters.debug_attrs.extend(all_attrs)

            if flags & BALANCED_TAGS:
                tag_name = lx.CanonicalTagName()
                if flags & NO_SPECIAL_TAGS:
                    tag_stack.append(tag_name)
                else:
                    # e.g. <meta> is considered self-closing, like <meta/>
                    if tag_name not in VOID_ELEMENTS:
                        tag_stack.append(tag_name)

            counters.max_tag_stack = max(counters.max_tag_stack,
                                         len(tag_stack))
        elif tok_id == h8_id.EndTag:
            if flags & BALANCED_TAGS:
                try:
                    expected = tag_stack.pop()
                except IndexError:
                    raise ParseError('Tag stack empty',
                                     s=contents,
                                     start_pos=start_pos)

                actual = lx.CanonicalTagName()
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


def ToXml(htm8_str):
    # type: (str) -> str

    # TODO:
    # 1. Lex it
    # 2. < & > must be escaped
    #    a. in raw data
    #    b. in quoted strings
    # 3. <script> turned into CDATA
    # 4. void tags turned into self-closing tags
    # 5. case-sensitive tag matching - not sure about this

    attr_lexer = htm8.AttrLexer(htm8_str)

    f = StringIO()
    out = Output(htm8_str, f)

    lx = Lexer(htm8_str)

    pos = 0
    while True:
        tok_id, end_pos = lx.Read()

        if tok_id == h8_id.Invalid:
            raise LexError('ToXml() got invalid token', htm8_str, pos)
        if tok_id == h8_id.EndOfStream:
            break

        if tok_id in (h8_id.RawData, h8_id.CharEntity, h8_id.HexChar,
                      h8_id.DecChar):
            out.PrintUntil(end_pos)
        elif tok_id in (h8_id.StartTag, h8_id.StartEndTag):
            attr_lexer.Init(tok_id, lx.TagNamePos(), end_pos)
            all_attrs = htm8.AllAttrsRawSlice(attr_lexer)
            for name_start, name_end, v, val_start, val_end in all_attrs:
                #val_lexer.Reset(val_start, val_end)
                pass
                # TODO: get the kind of string
                #
                # Quoted:   we need to replace & with &amp; and < with &lt;
                #           note > is not allowed
                # Unquoted: right now, we can just surround with double quotes
                #           because we don't allow any bad chars
                # Empty   : add "", so empty= becomes =""
                # Missing : add ="", so missing becomes missing=""

            tag_name = lx.CanonicalTagName()
            if tok_id == h8_id.StartTag and tag_name in VOID_ELEMENTS:
                # TODO: instead of closing >, print />
                pass

        elif tok_id == h8_id.BadAmpersand:
            #out.SkipTo(pos)
            out.Print('&amp;')
            out.SkipTo(end_pos)

        elif tok_id == h8_id.BadGreaterThan:
            #out.SkipTo(pos)
            out.Print('&gt;')
            out.SkipTo(end_pos)
        else:
            out.PrintUntil(end_pos)

        pos = end_pos

    out.PrintTheRest()
    return f.getvalue()


class Counters(object):

    def __init__(self):
        # type: () -> None
        self.num_tokens = 0
        self.num_start_tags = 0
        self.num_start_end_tags = 0
        self.num_attrs = 0
        self.max_tag_stack = 0
        self.num_val_tokens = 0

        #self.debug_attrs = []


#
# OLD TagLexer API - REMOVE THIS
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

# Similar to _UNQUOTED_VALUE in data_lang/htm8.py
_UNQUOTED_VALUE_OLD = r'''[^ \t\r\n<>&"'\x00]*'''

_TAG_RE = re.compile(r'/? \s* (%s)' % _NAME_RE, re.VERBOSE)

_TAG_LAST_RE = re.compile(r'\s* /? >', re.VERBOSE)

# To match href="foo"

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
''' % (_NAME_RE, _UNQUOTED_VALUE_OLD), re.VERBOSE)


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


def main(argv):
    # type: (List[str]) -> int
    action = argv[1]

    if action == 'tokens':
        contents = sys.stdin.read()

        lx = Lexer(contents)
        start_pos = 0
        while True:
            tok_id, end_pos = lx.Read()
            if tok_id == h8_id.Invalid:
                raise LexError('Invalid token', contents, start_pos)
            if tok_id == h8_id.EndOfStream:
                break

            frag = contents[start_pos:end_pos]
            log('%d %s %r', end_pos, h8_id_str(tok_id), frag)
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
