#!/usr/bin/env python2
"""ul_table.py: Markdown Tables Without New Syntax."""

import cStringIO

from doctools.util import log
from lazylex import html


class UlTableParser(object):

    def __init__(self, lexer, tag_lexer):
        self.lexer = lexer
        self.tag_lexer = tag_lexer

        self.tok_id = html.Invalid
        self.start_pos = 0
        self.end_pos = 0

    def _CurrentString(self):
        part = self.tag_lexer.s[self.start_pos:self.end_pos]
        return part

    def _Next(self):
        """
        Advance and set self.tok_id, self.start_pos, self.end_pos
        """
        self.start_pos = self.end_pos
        try:
            self.tok_id, self.end_pos = next(self.lexer)
        except StopIteration:
            raise
        if 0:
            part = self._CurrentString()
            log('[%3d - %3d] %r', self.start_pos, self.end_pos, part)

        #self.tok_id = html.EndOfStream
        # Don't change self.end_pos

    def _Eat(self, tok_id, s=None):
        """
        Advance, and assert we got the right input
        """

        # TODO:
        # - _EatTag()
        # - _EatRawData

        if self.tok_id != tok_id:
            raise html.ParseError('Expected token %s, got %s',
                                  html.TokenName(tok_id),
                                  html.TokenName(self.tok_id))
        if tok_id in (html.StartTag, html.EndTag):
            self.tag_lexer.Reset(self.start_pos, self.end_pos)
            tag_name = self.tag_lexer.TagName()
            if s is not None and s != tag_name:
                raise html.ParseError('Expected tag %r, got %r', s, tag_name)
        elif tok_id == html.RawData:
            actual = self._CurrentString()
            if s is not None and s != actual:
                raise html.ParseError('Expected data %r, got %r', s, actual)
        else:
            if s is not None:
                raise AssertionError("Don't know what to do with %r" % s)
        self._Next()

    def _WhitespaceOk(self):
        """
        Optional whitespace
        """
        if self.tok_id == html.RawData and self._CurrentString().isspace():
            self._Next()

    def FindUlTable(self):
        """Find <table ...> <ul>

        Return the START position of the <ul>
        Similar algorithm as html.ReadUntilStartTag()
        """
        tag_lexer = self.tag_lexer

        # Find first table
        while True:
            self._Next()
            if self.tok_id == html.EndOfStream:
                return -1

            tag_lexer.Reset(self.start_pos, self.end_pos)
            if (self.tok_id == html.StartTag and
                    tag_lexer.TagName() == 'table'):
                while True:
                    self._Next()
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
          [StartEndTag 'td-attrs']?
          ANY*               # NOT context-free - anything that's not the end
                             # This is what we should capture in CELLS
          [EndTag 'li']

        Example of attribute borrowing:

        - hi there          ==>
        <li>hi there</li>   ==>
        <td>hi there</td>

        - <td-attrs class=foo /> hi there          ==>
        <li><td-attrs class=foo /> hi there </li>  ==>
        <td class=foo> hi there </td>  ==>
        """
        self._WhitespaceOk()

        if self.tok_id != html.StartTag:
            return None, None

        inner_html = None
        td_attrs = None  # Can we also have col-attrs?

        self._Eat(html.StartTag, 'li')

        if self.tok_id == html.StartEndTag:
            self.tag_lexer.Reset(self.start_pos, self.end_pos)
            tag_name = self.tag_lexer.TagName()
            if tag_name != 'td-attrs':
                raise html.ParseError('Expected <td-attrs />, got %r' %
                                      tag_name)
            td_attrs = self.tag_lexer.AllAttrsRaw()
            self._Next()

        left = self.start_pos

        # Find the closing </li>
        balance = 0
        while True:
            # TODO: This has to  match NESTED
            # <li> <li>foo</li> </li>
            # Because cells can have bulleted lists

            if self.tok_id == html.StartTag:
                self.tag_lexer.Reset(self.start_pos, self.end_pos)
                if self.tag_lexer.TagName() == 'li':
                    balance += 1

            if self.tok_id == html.EndTag:
                self.tag_lexer.Reset(self.start_pos, self.end_pos)
                if self.tag_lexer.TagName() == 'li':
                    balance -= 1
                    if balance < 0:
                        break
            self._Next()

        right = self.start_pos  # start of the end tag

        inner_html = self.tag_lexer.s[left:right]
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
          [RawData thead\s*]
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

        # TODO: pass regex so it's tolerant to whitespace?
        self._Eat(html.RawData, 'thead\n')

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
            LIST_ITEM+        # Defined above
            [RawData \s*]?
            [EndTag 'ul']
        """
        #log('*** _ParseTr')

        cells = []

        self._WhitespaceOk()

        # Could be a </ul>
        if self.tok_id != html.StartTag:
            return None

        self._Eat(html.StartTag, 'li')

        # TODO: pass regex so it's tolerant to whitespace?
        self._Eat(html.RawData, 'tr\n')

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
        return cells

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

        thead = self._ParseTHead()
        #log('___ THEAD %s', thead)

        num_cells = len(thead)
        while True:
            tr = self._ParseTr()
            if tr is None:
                break
            # Not validating because of colspan
            if 0:
                if len(tr) != num_cells:
                    raise html.ParseError('Expected %d cells, got %d: %s',
                                          num_cells, len(tr), tr)

            #log('___ TR %s', tr)
            table['tr'].append(tr)

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

    thead_lookup = set()
    if thead_td_attrs:
        for name, raw_value in thead_td_attrs:
            thead_lookup.add(name)
            merged_attrs.append((name, raw_value))

    if row_td_attrs:
        for name, raw_value in row_td_attrs:
            if name in thead_lookup:
                raise html.ParseError('Duplicate attribute %r in thead and tr' %
                                 name)
            merged_attrs.append((name, raw_value))

    return merged_attrs


def ReplaceTables(s, debug_out=None):
    """
    ul-table: Write tables using bulleted list
    """
    if debug_out is None:
        debug_out = []

    f = cStringIO.StringIO()
    out = html.Output(s, f)

    tag_lexer = html.TagLexer(s)
    it = html.ValidTokens(s)

    p = UlTableParser(it, tag_lexer)

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
        out.Print('<thead>\n')
        out.Print('<tr>\n')

        col_attrs = {}  # integer -> td_attrs

        i = 0
        for td_attrs, raw_html in table['thead']:
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
        for row in table['tr']:
            out.Print('<tr>\n')
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
