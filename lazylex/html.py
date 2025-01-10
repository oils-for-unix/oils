#!/usr/bin/env python2
"""
lazylex/html.py - Low-Level HTML Processing.

See lazylex/README.md for details.

TODO: This should be an Oils library eventually.  It's a "lazily-parsed data
structure" like TSV8
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
        else:
            snippet = ''
        return '(ParseError %r %r)' % (self.msg, snippet)


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

LEXER = [
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

    # NOTE: < is allowed in these?
    (r'<! [^>]+ >', Tok.Decl),  # <!DOCTYPE html>

    # Tags
    # Notes:
    # - We look for a valid tag name, but we don't validate attributes.
    #   That's done in the tag lexer.
    # - We don't allow leading whitespace
    (r'</ (%s) >' % _NAME, Tok.EndTag),
    # self-closing <br/>  comes before StarttTag
    (r'<  (%s) [^>]* />' % _NAME, Tok.StartEndTag),  # end </a>
    (r'<  (%s) [^>]* >' % _NAME, Tok.StartTag),  # start <a>

    # Characters
    # https://www.w3.org/TR/xml/#sec-references
    (r'&\# [0-9]+ ;', Tok.DecChar),
    (r'&\# x[0-9a-fA-F]+ ;', Tok.HexChar),
    (r'& %s ;' % _NAME, Tok.CharEntity),

    # HTML5 allows unescaped > in raw data, but < is not allowed.
    # https://stackoverflow.com/questions/10462348/right-angle-bracket-in-html
    #
    # - My early blog has THREE errors when disallowing >
    # - So do some .wwz files
    (r'[^&<]+', Tok.RawData),
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

    def __init__(self, s, left_pos=0, right_pos=-1):
        self.s = s
        self.pos = left_pos
        self.right_pos = len(s) if right_pos == -1 else right_pos
        self.cache = {}  # string -> compiled regex pattern object

        # either </script> or </style> - we search until we see that
        self.search_state = None  # type: Optional[str]

    def _Peek(self):
        # type: () -> Tuple[int, int]
        """
        Note: not using _Peek() now
        """
        if self.pos == self.right_pos:
            return Tok.EndOfStream, self.pos

        assert self.pos < self.right_pos, self.pos

        if self.search_state is not None:
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
                    tag_name = m.group(1)  # captured
                    if tag_name == 'script':
                        self.search_state = '</script>'
                    elif tag_name == 'style':
                        self.search_state = '</style>'

                return tok_id, m.end()
        else:
            raise AssertionError('Tok.Invalid rule should have matched')

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

_ATTR_VALUE = r'[a-zA-Z0-9_\-]+'  # allow hyphens

# TODO: we don't need to capture the tag name here?  That's done at the top
# level
_TAG_RE = re.compile(r'/? \s* (%s)' % _NAME, re.VERBOSE)

# To match href="foo"

_ATTR_RE = re.compile(
    r'''
\s+                     # Leading whitespace is required
(%s)                    # Attribute name
(?:                     # Optional attribute value
  \s* = \s*
  (?:
    " ([^>"]*) "        # double quoted value
  | (%s)                # Attribute value
                        # TODO: relax this?  for href=$foo
  )
)?             
''' % (_NAME, _ATTR_VALUE), re.VERBOSE)

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


def main(argv):
    action = argv[1]

    if action in ('lex-tags', 'lex-attrs', 'lex-attr-values', 'well-formed'):
        num_tokens = 0
        num_start_tags = 0
        num_start_end_tags = 0
        num_attrs = 0
        max_tag_stack = 0

        errors = []
        i = 0
        for line in sys.stdin:
            name = line.strip()
            with open(name) as f:
                contents = f.read()

            tag_lexer = TagLexer(contents)
            lx = ValidTokens(contents)
            tokens = []
            start_pos = 0
            tag_stack = []
            try:
                for tok_id, end_pos in lx:
                    tokens.append((tok_id, end_pos))
                    if tok_id == Tok.StartEndTag:
                        num_start_end_tags += 1
                        if action in ('lex-attrs', 'lex-attr-values',
                                      'well-formed'):
                            tag_lexer.Reset(start_pos, end_pos)
                            all_attrs = tag_lexer.AllAttrsRaw()
                            num_attrs += len(all_attrs)
                    elif tok_id == Tok.StartTag:
                        num_start_tags += 1
                        if action in ('lex-attrs', 'lex-attr-values',
                                      'well-formed'):
                            tag_lexer.Reset(start_pos, end_pos)
                            all_attrs = tag_lexer.AllAttrsRaw()

                            # TODO: we need to get the tag name here
                            tag_stack.append('TODO')
                            max_tag_stack = max(max_tag_stack, len(tag_stack))
                    elif tok_id == Tok.EndTag:
                        try:
                            expected = tag_stack.pop()
                        except IndexError:
                            raise ParseError('Tag stack empty',
                                             s=contents,
                                             start_pos=start_pos)

                        # TODO: we need to get the tag name here
                        actual = 'TODO'
                        if expected != actual:
                            raise ParseError(
                                'Expected closing tag %r, got %r' %
                                (expected, actual),
                                s=contents,
                                start_pos=start_pos)

                    start_pos = end_pos
            except LexError as e:
                log('Lex error in %r: %s', name, e)
                errors.append((name, e))
            except ParseError as e:
                log('Parse error in %r: %s', name, e)
                errors.append((name, e))
            else:
                num_tokens += len(tokens)

            #print('%d %s' % (len(tokens), name))
            i += 1

        log('')
        log(
            '  %d tokens, %d start/end tags, %d start tags, %d attrs, %d max tag stack depth in %d files',
            num_tokens, num_start_end_tags, num_start_tags, num_attrs,
            max_tag_stack, i)
        log('  %d errors', len(errors))
        if 0:
            for name, e in errors:
                log('Error in %r: %s', name, e)

    else:
        raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
    main(sys.argv)
