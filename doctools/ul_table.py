#!/usr/bin/env python2
"""ul_table.py: Markdown Tables Without New Syntax."""

from _devbuild.gen.htm8_asdl import h8_id, h8_id_t, h8_id_str

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO  # type: ignore
import re
import sys

from doctools.util import log
from data_lang import htm8
from typing import List
from typing import Optional
from typing import Tuple
from typing import Any
from typing import Dict


def RemoveComments(s):
    # type: (str) -> str
    """Remove <!-- comments -->

    This is a required preprocessing step for ul-table.
    """
    f = StringIO()
    out = htm8.Output(s, f)
    lx = htm8.Lexer(s)

    pos = 0
    while True:
        tok_id, end_pos = lx.Read()
        if tok_id == h8_id.EndOfStream:
            break

        if tok_id == h8_id.Invalid:
            raise htm8.LexError('RemoveComments() got invalid token', s, pos)

        if tok_id == h8_id.Comment:
            value = s[pos:end_pos]
            # doc/release-index.md has <!-- REPLACE_WITH_DATE --> etc.
            if 'REPLACE' not in value:
                out.PrintUntil(pos)
                out.SkipTo(end_pos)
        pos = end_pos

    out.PrintTheRest()
    return f.getvalue()


_WHITESPACE_RE = re.compile(r'\s*')

TdAttrs = List[Tuple[str, str]]


class UlTableParser(object):

    def __init__(self, lexer):
        # type: (htm8.Lexer) -> None
        self.lexer = lexer
        self.attr_lexer = htm8.AttrLexer(lexer.s)

        self.tok_id = h8_id.Invalid
        self.start_pos = 0
        self.end_pos = 0
        # The tag name is only populated when we are "looking at"
        # h8_id.{StartTag,EndTag,StartEndTag}
        self.tag_name = None  # type: Optional[str]

    def _CurrentString(self):
        # type: () -> str
        part = self.lexer.s[self.start_pos:self.end_pos]
        return part

    def _Next(self, comment_ok=False):
        # type: (bool) -> None
        """
        Advance and set self.tok_id, self.start_pos, self.end_pos
        """
        self.start_pos = self.end_pos
        self.tok_id, self.end_pos = self.lexer.Read()
        if self.tok_id in (h8_id.StartTag, h8_id.EndTag, h8_id.StartEndTag):
            self.tag_name = self.lexer.CanonicalTagName()
        else:
            self.tag_name = None

        # Should have called RemoveComments() beforehand.  That can still leave
        # some REPLACE cmoments
        if not comment_ok and self.tok_id == h8_id.Comment:
            raise htm8.ParseError('Unexpected HTML comment')

        if 0:
            part = self._CurrentString()
            log('[%3d - %3d] %r', self.start_pos, self.end_pos, part)

    def _EatRawData(self, regex):
        # type: (str) -> None
        """
        Assert that we got text data matching a regex, and advance
        """
        if self.tok_id != h8_id.RawData:
            raise htm8.ParseError('Expected RawData, got %s' %
                                  h8_id_str(self.tok_id))
        actual = self._CurrentString()
        m = re.match(regex, actual)  # could compile this
        if m is None:
            raise htm8.ParseError('Expected to match %r, got %r' %
                                  (regex, actual))
        self._Next()

    def _Eat(self, expected_id, expected_tag):
        # type: (h8_id_t, str) -> None
        """
        Assert that we got a start or end tag, with the given name, and advance

        Args:
          expected_id: h8_id.StartTag or h8_id.EndTag
          expected_tag: 'a', 'span', etc.
        """
        assert expected_id in (h8_id.StartTag,
                               h8_id.EndTag), h8_id_str(expected_id)

        if self.tok_id != expected_id:
            raise htm8.ParseError(
                'Expected token %s, got %s' %
                (h8_id_str(expected_id), h8_id_str(self.tok_id)))
        if expected_tag != self.tag_name:
            raise htm8.ParseError('Expected tag %r, got %r' %
                                  (expected_tag, self.tag_name))

        self._Next()

    def _WhitespaceOk(self):
        # type: () -> None
        """
        Optional whitespace
        """
        if (self.tok_id == h8_id.RawData and
                _WHITESPACE_RE.match(self.lexer.s, self.start_pos)):
            self._Next()

    def FindUlTable(self):
        # type: () -> int
        """Find <table ...> <ul>

        Return the START position of the <ul>
        Similar algorithm as html.ReadUntilStartTag()
        """
        # Find first table
        while True:
            self._Next(comment_ok=True)
            if self.tok_id == h8_id.EndOfStream:
                return -1

            if (self.tok_id == h8_id.StartTag and self.tag_name == 'table'):
                while True:
                    self._Next(comment_ok=True)
                    if self.tok_id != h8_id.RawData:
                        break

                if (self.tok_id == h8_id.StartTag and self.tag_name == 'ul'):
                    return self.start_pos
        return -1

    def _ListItem(self):
        # type: () -> Tuple[Optional[TdAttrs], Optional[str]]
        """Parse a list item nested below thead or tr.

        Returns:
            A pair (td_attrs, inner_html)

        Grammar:

        LIST_ITEM =
          [RawData \s*]?
          [StartTag 'li']
          ANY*               # NOT context-free:
                             # - we MATCH <li> and </li> with a tack
                             # - We search for [StartEndTag 'cell-attrs']?
          [EndTag 'li']

        Example of attribute borrowing:

        - hi there          ==>
        <li>hi there</li>   ==>
        <td>hi there</td>

        - <cell-attrs class=foo /> hi there          ==>
        <li><cell-attrs class=foo /> hi there </li>  ==>
        <td class=foo> hi there </td>  ==>
        """
        self._WhitespaceOk()

        if self.tok_id != h8_id.StartTag:
            return None, None

        inner_html = None
        td_attrs = None  # Can we also have col-attrs?
        td_attrs_span = None

        self._Eat(h8_id.StartTag, 'li')

        left = self.start_pos

        # Find the closing </li>, taking into accounted NESTED tags:
        #    <li> <li>foo</li> </li>
        # because cells can have bulleted lists
        balance = 0
        while True:
            if self.tok_id == h8_id.StartEndTag:
                self.attr_lexer.Init(self.tok_id, self.lexer.TagNamePos(),
                                     self.end_pos)
                # TODO: remove td-attrs backward compat
                if self.tag_name in ('td-attrs', 'cell-attrs'):
                    td_attrs_span = self.start_pos, self.end_pos
                    td_attrs = htm8.AllAttrsRaw(self.attr_lexer)
                    #log('CELL ATTRS %r', self._CurrentString())

            elif self.tok_id == h8_id.StartTag:
                if self.tag_name == 'li':
                    balance += 1

            elif self.tok_id == h8_id.EndTag:
                if self.tag_name == 'li':
                    balance -= 1
                    if balance < 0:
                        break
            self._Next()

        right = self.start_pos  # start of the end tag

        s = self.lexer.s
        if td_attrs_span:
            # everything except the <cell-attrs />
            inner_html = s[left:td_attrs_span[0]] + s[td_attrs_span[1]:right]
            #log('LEFT %r', s[left:td_attrs_span[0]])
            #log('RIGHT %r', s[td_attrs_span[1]:right])
        else:
            inner_html = s[left:right]
        #log('RAW inner html %r', inner_html)

        #self._Eat(h8_id.EndTag, 'li')
        self._Next()

        return td_attrs, inner_html

    def _ParseTHead(self):
        # type: () -> List[Tuple[Optional[TdAttrs], str]]
        """
        Assume we're looking at the first <ul> tag.  Now we want to find
        <li>thead and the nested <ul>

        Grammar:

        THEAD = 
          [StartTag 'ul']
          [RawData \s*]?
          [StartTag 'li']
          [RawData thead\s*]
            [StartTag 'ul']   # Indented bullet that starts -
            LIST_ITEM+
            [RawData \s*]?
            [EndTag 'ul']
          [RawData thead\s+]
          [End 'li']

        Two Algorithms:

        1. Replacement:
           - skip over the first ul 'thead' li, and ul 'tr' li
           - then replace the next ul -> tr, and li -> td
        2. Parsing and Rendering:
           - parse them into a structure
           - skip all the text
           - print your own HTML

        I think the second one is better, because it allows attribute extensions
        to thead

        - thead
          - name [link][]
            - colgroup=foo align=left
          - age
            - colgroup=foo align=right
        """
        #log('*** _ParseTHead')
        cells = []

        self._WhitespaceOk()
        self._Eat(h8_id.StartTag, 'li')

        # In CommonMark, r'thead\n' is enough, because it strips trailing
        # whitespace.  I'm not sure if other Markdown processors do that, so
        # use r'thead\s+'.
        self._EatRawData(r'thead\s+')

        # This is the row data
        self._Eat(h8_id.StartTag, 'ul')

        while True:
            td_attrs, inner_html = self._ListItem()
            if inner_html is None:
                break
            cells.append((td_attrs, inner_html))
        self._WhitespaceOk()

        self._Eat(h8_id.EndTag, 'ul')

        self._WhitespaceOk()
        self._Eat(h8_id.EndTag, 'li')

        #log('_ParseTHead %s ', html.TOKEN_NAMES[self.tok_id])
        return cells

    def _ParseTr(self):
        # type: () -> Tuple[Optional[TdAttrs], List[Tuple[Optional[TdAttrs], str]]]
        """
        Assume we're looking at the first <ul> tag.  Now we want to find
        <li>tr and the nested <ul>

        Grammar:

        TR = 
          [RawData \s*]?
          [StartTag 'li']
          [RawData thead\s*]
            [StartTag 'ul']   # Indented bullet that starts -
            ( [StartEndTag row-attrs] [RawData \s*] )? 
            LIST_ITEM+        # Defined above
            [RawData \s*]?
            [EndTag 'ul']
        """
        #log('*** _ParseTr')

        cells = []

        self._WhitespaceOk()

        # Could be a </ul>
        if self.tok_id != h8_id.StartTag:
            return None, None

        self._Eat(h8_id.StartTag, 'li')

        self._EatRawData(r'tr\s*')

        tr_attrs = None
        if self.tok_id == h8_id.StartEndTag:
            self.attr_lexer.Init(self.tok_id, self.lexer.TagNamePos(),
                                 self.end_pos)
            if self.tag_name != 'row-attrs':
                raise htm8.ParseError('Expected row-attrs, got %r' %
                                      self.tag_name)
            tr_attrs = htm8.AllAttrsRaw(self.attr_lexer)
            self._Next()
            self._WhitespaceOk()

        # This is the row data
        self._Eat(h8_id.StartTag, 'ul')

        while True:
            td_attrs, inner_html = self._ListItem()
            if inner_html is None:
                break
            cells.append((td_attrs, inner_html))
            # TODO: assert

        self._WhitespaceOk()

        self._Eat(h8_id.EndTag, 'ul')

        self._WhitespaceOk()
        self._Eat(h8_id.EndTag, 'li')

        #log('_ParseTHead %s ', html.TOKEN_NAMES[self.tok_id])
        return tr_attrs, cells

    def ParseTable(self):
        # type: () -> Dict[str, Any]
        """
        Returns a structure like this
        { 'thead': [ 'col1', 'col2' ],  # TODO: columns can have CSS attributes
          'tr': [                       # raw HTML that you surround with <td>
            [ 'cell1 html', 'cell2 html' ], 
            [ 'cell1 html', 'cell2 html' ],
          ]
        }

        Grammar:

        UL_TABLE =
          [StartTag 'ul']
          THEAD   # this this returns the number of cells, so it's NOT context
                  # free
          TR*     
          [EndTag 'ul']
        """
        table = {'tr': []}  # type: Dict[str, Any]

        ul_start = self.start_pos
        self._Eat(h8_id.StartTag, 'ul')

        # Look ahead 2 or 3 tokens:
        if self.lexer.LookAhead(r'\s*<li>thead\s+'):
            thead = self._ParseTHead()
        else:
            thead = None
        #log('___ THEAD %s', thead)

        while True:
            tr_attrs, tr = self._ParseTr()
            if tr is None:
                break
            # Not validating because of colspan
            if 0:
                if thead and len(tr) != len(thead):
                    raise htm8.ParseError('Expected %d cells, got %d: %s' %
                                          (len(thead), len(tr), tr))

            #log('___ TR %s', tr)
            table['tr'].append((tr_attrs, tr))

        self._Eat(h8_id.EndTag, 'ul')

        self._WhitespaceOk()

        ul_end = self.start_pos

        table['thead'] = thead
        table['ul_start'] = ul_start
        table['ul_end'] = ul_end

        if 0:
            log('table %s', table)
            from pprint import pprint
            pprint(table)

        return table


def MergeAttrs(
        thead_td_attrs,  # type: Optional[TdAttrs]
        row_td_attrs,  # type: Optional[TdAttrs]
):
    # type: (...) -> TdAttrs
    merged_attrs = []

    if row_td_attrs is None:
        row_lookup = {}
    else:
        row_lookup = {n: v for n, v in row_td_attrs}

    done_for_row = set()

    if thead_td_attrs:
        for name, raw_value in thead_td_attrs:
            more_values = row_lookup.get(name)
            if more_values is not None:
                raw_value += ' %s' % more_values
                done_for_row.add(name)
            merged_attrs.append((name, raw_value))

    if row_td_attrs:
        for name, raw_value in row_td_attrs:
            if name in done_for_row:
                continue
            merged_attrs.append((name, raw_value))

    return merged_attrs


def ReplaceTables(s, debug_out=None):
    # type: (str, Optional[Any]) -> str
    """
    ul-table: Write tables using bulleted list
    """
    if debug_out is None:
        debug_out = []

    f = StringIO()
    out = htm8.Output(s, f)

    lexer = htm8.Lexer(s)

    p = UlTableParser(lexer)

    while True:
        ul_start = p.FindUlTable()
        if ul_start == -1:
            break

        #log('UL START %d', ul_start)
        out.PrintUntil(ul_start)

        table = p.ParseTable()
        #log('UL END %d', ul_end)

        # Don't write the matching </u> of the LAST row, but write everything
        # after that
        out.SkipTo(table['ul_end'])

        # Write the header
        thead = table['thead']

        col_attrs = {}  # integer -> td_attrs
        if thead:
            out.Print('<thead>\n')
            out.Print('<tr>\n')

            i = 0
            for td_attrs, raw_html in thead:
                if td_attrs:
                    col_attrs[i] = td_attrs
                # <th> tag is more semantic, and styled bold by default
                out.Print('  <th>')
                out.Print(raw_html)
                out.Print('</th>\n')
                i += 1

            out.Print('</tr>\n')
            out.Print('</thead>\n')

        # Write each row
        for tr_attrs, row in table['tr']:

            # Print tr tag and attrs
            out.Print('<tr')
            if tr_attrs:
                for name, raw_value in tr_attrs:
                    out.Print(' ')
                    out.Print(name)
                    # No escaping because it's raw.  It can't contain quotes.
                    out.Print('="%s"' % raw_value)
            out.Print('>\n')

            # Print cells
            i = 0
            for row_td_attrs, raw_html in row:
                # Inherited from header
                thead_td_attrs = col_attrs.get(i)
                merged_attrs = MergeAttrs(thead_td_attrs, row_td_attrs)

                out.Print('  <td')
                for name, raw_value in merged_attrs:
                    out.Print(' ')
                    out.Print(name)
                    # No escaping because it's raw.  It can't contain quotes.
                    out.Print('="%s"' % raw_value)
                out.Print('>')

                out.Print(raw_html)
                out.Print('</td>\n')
                i += 1
            out.Print('</tr>\n')

    out.PrintTheRest()

    return f.getvalue()


if __name__ == '__main__':
    # Simple CLI filter
    h = sys.stdin.read()
    h = RemoveComments(h)
    h = ReplaceTables(h)
    sys.stdout.write(h)
