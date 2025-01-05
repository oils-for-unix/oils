#!/usr/bin/env python2
"""ul_table.py: Markdown Tables Without New Syntax."""

try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO
import re
import sys

from doctools.util import log
from lazylex import html


def RemoveComments(s):
    """Remove <!-- comments -->

    This is a required preprocessing step for ul-table.
    """
    f = StringIO()
    out = html.Output(s, f)

    tag_lexer = html.TagLexer(s)

    pos = 0

    for tok_id, end_pos in html.ValidTokens(s):
        if tok_id == html.Comment:
            value = s[pos:end_pos]
            # doc/release-index.md has <!-- REPLACE_WITH_DATE --> etc.
            if 'REPLACE' not in value:
                out.PrintUntil(pos)
                out.SkipTo(end_pos)
        pos = end_pos

    out.PrintTheRest()
    return f.getvalue()


_WHITESPACE_RE = re.compile(r'\s*')


class UlTableParser(object):

    def __init__(self, lexer, tag_lexer):
        self.lexer = lexer
        self.tag_lexer = tag_lexer

        self.tok_id = html.Invalid
        self.start_pos = 0
        self.end_pos = 0

    def _CurrentString(self):
        part = self.lexer.s[self.start_pos:self.end_pos]
        return part

    def _Next(self, comment_ok=False):
        """
        Advance and set self.tok_id, self.start_pos, self.end_pos
        """
        self.start_pos = self.end_pos
        self.tok_id, self.end_pos = self.lexer.Read()

        # Should have called RemoveComments() beforehand.  That can still leave
        # some REPLACE cmoments
        if not comment_ok and self.tok_id == html.Comment:
            raise html.ParseError('Unexpected HTML comment')

        if 0:
            part = self._CurrentString()
            log('[%3d - %3d] %r', self.start_pos, self.end_pos, part)

    def _EatRawData(self, regex):
        # type: (str) -> None
        """
        Assert that we got text data matching a regex, and advance
        """
        if self.tok_id != html.RawData:
            raise html.ParseError('Expected RawData, got %s',
                                  html.TokenName(self.tok_id))
        actual = self._CurrentString()
        m = re.match(regex, actual)  # could compile this
        if m is None:
            raise html.ParseError('Expected to match %r, got %r', regex,
                                  actual)
        self._Next()

    def _Eat(self, expected_id, expected_tag):
        """
        Assert that we got a start or end tag, with the given name, and advance

        Args:
          expected_id: html.StartTag or html.EndTag
          expected_tag: 'a', 'span', etc.
        """
        assert expected_id in (html.StartTag,
                               html.EndTag), html.TokenName(expected_id)

        if self.tok_id != expected_id:
            raise html.ParseError('Expected token %s, got %s',
                                  html.TokenName(expected_id),
                                  html.TokenName(self.tok_id))
        self.tag_lexer.Reset(self.start_pos, self.end_pos)
        tag_name = self.tag_lexer.TagName()
        if expected_tag != tag_name:
            raise html.ParseError('Expected tag %r, got %r', expected_tag,
                                  tag_name)

        self._Next()

    def _WhitespaceOk(self):
        """
        Optional whitespace
        """
        if (self.tok_id == html.RawData and
                _WHITESPACE_RE.match(self.lexer.s, self.start_pos)):
            self._Next()

    def FindUlTable(self):
        """Find <table ...> <ul>

        Return the START position of the <ul>
        Similar algorithm as html.ReadUntilStartTag()
        """
        tag_lexer = self.tag_lexer

        # Find first table
        while True:
            self._Next(comment_ok=True)
            if self.tok_id == html.EndOfStream:
                return -1

            tag_lexer.Reset(self.start_pos, self.end_pos)
            if (self.tok_id == html.StartTag and
                    tag_lexer.TagName() == 'table'):
                while True:
                    self._Next(comment_ok=True)
                    if self.tok_id != html.RawData:
                        break

                tag_lexer.Reset(self.start_pos, self.end_pos)
                if (self.tok_id == html.StartTag and
                        tag_lexer.TagName() == 'ul'):
                    return self.start_pos
        return -1

    def _ListItem(self):
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

        if self.tok_id != html.StartTag:
            return None, None

        inner_html = None
        td_attrs = None  # Can we also have col-attrs?
        td_attrs_span = None

        self._Eat(html.StartTag, 'li')

        left = self.start_pos

        # Find the closing </li>, taking into accounted NESTED tags:
        #    <li> <li>foo</li> </li>
        # because cells can have bulleted lists
        balance = 0
        while True:
            if self.tok_id == html.StartEndTag:
                self.tag_lexer.Reset(self.start_pos, self.end_pos)
                tag_name = self.tag_lexer.TagName()
                # TODO: remove td-attrs backward compat
                if tag_name in ('td-attrs', 'cell-attrs'):
                    td_attrs_span = self.start_pos, self.end_pos
                    td_attrs = self.tag_lexer.AllAttrsRaw()
                    #log('CELL ATTRS %r', self._CurrentString())

            elif self.tok_id == html.StartTag:
                self.tag_lexer.Reset(self.start_pos, self.end_pos)
                if self.tag_lexer.TagName() == 'li':
                    balance += 1

            elif self.tok_id == html.EndTag:
                self.tag_lexer.Reset(self.start_pos, self.end_pos)
                if self.tag_lexer.TagName() == 'li':
                    balance -= 1
                    if balance < 0:
                        break
            self._Next()

        right = self.start_pos  # start of the end tag

        s = self.tag_lexer.s
        if td_attrs_span:
            # everything except the <cell-attrs />
            inner_html = s[left:td_attrs_span[0]] + s[td_attrs_span[1]:right]
            #log('LEFT %r', s[left:td_attrs_span[0]])
            #log('RIGHT %r', s[td_attrs_span[1]:right])
        else:
            inner_html = s[left:right]
        #log('RAW inner html %r', inner_html)

        #self._Eat(html.EndTag, 'li')
        self._Next()

        return td_attrs, inner_html

    def _ParseTHead(self):
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
        self._Eat(html.StartTag, 'li')

        # In CommonMark, r'thead\n' is enough, because it strips trailing
        # whitespace.  I'm not sure if other Markdown processors do that, so
        # use r'thead\s+'.
        self._EatRawData(r'thead\s+')

        # This is the row data
        self._Eat(html.StartTag, 'ul')

        while True:
            td_attrs, inner_html = self._ListItem()
            if inner_html is None:
                break
            cells.append((td_attrs, inner_html))
        self._WhitespaceOk()

        self._Eat(html.EndTag, 'ul')

        self._WhitespaceOk()
        self._Eat(html.EndTag, 'li')

        #log('_ParseTHead %s ', html.TOKEN_NAMES[self.tok_id])
        return cells

    def _ParseTr(self):
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
        if self.tok_id != html.StartTag:
            return None, None

        self._Eat(html.StartTag, 'li')

        self._EatRawData(r'tr\s*')

        tr_attrs = None
        if self.tok_id == html.StartEndTag:
            self.tag_lexer.Reset(self.start_pos, self.end_pos)
            tag_name = self.tag_lexer.TagName()
            if tag_name != 'row-attrs':
                raise html.ParseError('Expected row-attrs, got %r' % tag_name)
            tr_attrs = self.tag_lexer.AllAttrsRaw()
            self._Next()
            self._WhitespaceOk()

        # This is the row data
        self._Eat(html.StartTag, 'ul')

        while True:
            td_attrs, inner_html = self._ListItem()
            if inner_html is None:
                break
            cells.append((td_attrs, inner_html))
            # TODO: assert

        self._WhitespaceOk()

        self._Eat(html.EndTag, 'ul')

        self._WhitespaceOk()
        self._Eat(html.EndTag, 'li')

        #log('_ParseTHead %s ', html.TOKEN_NAMES[self.tok_id])
        return tr_attrs, cells

    def ParseTable(self):
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
        table = {'tr': []}

        ul_start = self.start_pos
        self._Eat(html.StartTag, 'ul')

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
                    raise html.ParseError('Expected %d cells, got %d: %s',
                                          len(thead), len(tr), tr)

            #log('___ TR %s', tr)
            table['tr'].append((tr_attrs, tr))

        self._Eat(html.EndTag, 'ul')

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


def MergeAttrs(thead_td_attrs, row_td_attrs):
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
    """
    ul-table: Write tables using bulleted list
    """
    if debug_out is None:
        debug_out = []

    f = StringIO()
    out = html.Output(s, f)

    tag_lexer = html.TagLexer(s)
    lexer = html.Lexer(s)

    p = UlTableParser(lexer, tag_lexer)

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
