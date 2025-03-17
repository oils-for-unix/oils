#!/usr/bin/env python2

try:
    from cStringIO import StringIO
except ImportError:
    # for python3
    from io import StringIO  # type: ignore
import sys

from typing import List

from _devbuild.gen.htm8_asdl import (h8_id, h8_id_str, attr_value_e)
from data_lang import htm8
from data_lang.htm8 import (Lexer, LexError, ParseError, Output)
from doctools.util import log

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

NO_LEX_ATTRS = 1 << 1  # skip href="?x=42&amp;y=99"
NO_SPECIAL_TAGS = 1 << 2  # <script> <style>, VOID tags, etc.
BALANCED_TAGS = 1 << 3  # are tags balanced?


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
            if not bool(flags & NO_LEX_ATTRS):
                all_attrs = htm8.AllAttrsRaw(attr_lx)
                counters.num_attrs += len(all_attrs)
            # TODO: val_lexer.NumTokens() can be replaced with tokens_out

        elif tok_id == h8_id.StartTag:
            counters.num_start_tags += 1

            attr_lx.Init(tok_id, lx.TagNamePos(), end_pos)
            if not bool(flags & NO_LEX_ATTRS):
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
            for name_start, name_end, equal_end, v, val_start, val_end in all_attrs:
                if v == attr_value_e.Missing:  # <a missing>
                    out.PrintUntil(name_end)
                    out.Print('=""')
                elif v == attr_value_e.Empty:  # <a empty=>
                    out.PrintUntil(equal_end)
                    out.Print('""')
                elif v == attr_value_e.Unquoted:  # <a foo=bar>
                    # Because we disallow ", we can just surround with quotes
                    out.PrintUntil(val_start)
                    out.Print('"')
                    out.PrintUntil(val_end)
                    out.Print('"')

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

    elif action in ('quick-scan', 'lex-htm8', 'parse-htm8', 'parse-xml'):

        errors = []
        counters = Counters()

        flags = 0
        if action == 'quick-scan':
            flags |= NO_LEX_ATTRS
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
