#!/usr/bin/env python2
"""
lazylex/html.py - Wrapper around HTM8

See doc/lazylex.md for details.

"""
from __future__ import print_function

from _devbuild.gen.htm8_asdl import (h8_id, h8_id_t, h8_id_str)
from data_lang.htm8 import (Lexer, TagLexer, AttrValueLexer, LexError,
                            ParseError, Output)
from doctools.util import log

try:
    from cStringIO import StringIO
except ImportError:
    # for python3
    from io import StringIO  # type: ignore
import sys

if sys.version_info.major == 2:
    from typing import List, Tuple, Iterator


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
            raise LexError(s, pos)
        yield tok_id, end_pos
        pos = end_pos


def ValidTokenList(s, no_special_tags=False):
    # type: (str, bool) -> List[Tuple[h8_id_t, int]]
    """A wrapper that can be more easily translated to C++.  Doesn't use iterators."""

    start_pos = 0
    tokens = []
    lx = Lexer(s, no_special_tags=no_special_tags)
    while True:
        tok_id, end_pos = lx.Read()
        tokens.append((tok_id, end_pos))
        if tok_id == h8_id.EndOfStream:
            break
        if tok_id == h8_id.Invalid:
            raise LexError(s, start_pos)
        start_pos = end_pos
    return tokens


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

    tag_lexer = TagLexer(contents)
    val_lexer = AttrValueLexer(contents)

    no_special_tags = bool(flags & NO_SPECIAL_TAGS)
    lx = Lexer(contents, no_special_tags=no_special_tags)
    tokens = []
    start_pos = 0
    tag_stack = []
    while True:
        tok_id, end_pos = lx.Read()
        #log('TOP %s %r', h8_id_str(tok_id), contents[start_pos:end_pos])

        if tok_id == h8_id.Invalid:
            raise LexError(contents, start_pos)
        if tok_id == h8_id.EndOfStream:
            break

        tokens.append((tok_id, end_pos))

        if tok_id == h8_id.StartEndTag:
            counters.num_start_end_tags += 1

            tag_lexer.Reset(start_pos, end_pos)
            all_attrs = tag_lexer.AllAttrsRawSlice()
            counters.num_attrs += len(all_attrs)
            for name, val_start, val_end in all_attrs:
                val_lexer.Reset(val_start, val_end)
                counters.num_val_tokens += val_lexer.NumTokens()

            #counters.debug_attrs.extend(all_attrs)

        elif tok_id == h8_id.StartTag:
            counters.num_start_tags += 1

            tag_lexer.Reset(start_pos, end_pos)
            all_attrs = tag_lexer.AllAttrsRawSlice()
            counters.num_attrs += len(all_attrs)
            for name, val_start, val_end in all_attrs:
                val_lexer.Reset(val_start, val_end)
                counters.num_val_tokens += val_lexer.NumTokens()

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

    tag_lexer = TagLexer(htm8_str)
    val_lexer = AttrValueLexer(htm8_str)

    f = StringIO()
    out = Output(htm8_str, f)

    lx = Lexer(htm8_str)

    pos = 0
    while True:
        tok_id, end_pos = lx.Read()

        if tok_id == h8_id.Invalid:
            raise LexError(htm8_str, pos)
        if tok_id == h8_id.EndOfStream:
            break

        if tok_id in (h8_id.RawData, h8_id.CharEntity, h8_id.HexChar,
                      h8_id.DecChar):
            out.PrintUntil(end_pos)
        elif tok_id in (h8_id.StartTag, h8_id.StartEndTag):
            tag_lexer.Reset(pos, end_pos)
            # TODO: reduce allocations here
            all_attrs = tag_lexer.AllAttrsRawSlice()
            for name, val_start, val_end in all_attrs:
                val_lexer.Reset(val_start, val_end)
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
                raise LexError(contents, start_pos)
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
