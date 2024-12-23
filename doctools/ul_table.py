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
        """
        LIST_ITEM =
          [RawData \s*]?
          [StartTag 'li']
          [StartEndTag 'td-attrs']?
          ANY*               # NOT context-free - anything that's not the end
                             # This is what we should capture in CELLS
          [EndTag 'li']

        Example:

        - hi there          ==>
        <li>hi there</li>   ==>
        <td>hi there</td>

        - <td-attrs class=foo /> hi there          ==>
        <li><td-attrs class=foo /> hi there </li>  ==>
        <td class=foo> hi there </td>  ==>

        That is, the attributes are borrowed.

        TODO: TagLexer() needs a method to copy everything except the tag name,
        i.e. all the attributes.

        We can then return a pair (attr_string, inner_html)

        TODO:
        - We may need to merge "class" attributes?

        - thead
          - <td-attrs class=first-col />
          - other
          - <td-attrs class=zulip-col />
        - tr
          - <td-attrs class=more />
          - other
          - <td-attrs class=more />

        To start, we could assert that the attrs in thead and tr are DISJOINT?
        More tables probably don't need it.
        """
        self._WhitespaceOk()

        if self.tok_id != html.StartTag:
            return None

        self._Eat(html.StartTag, 'li')

        left = self.start_pos

        # Any tag except end tag
        inner_html = None
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

        return inner_html

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
            inner_html = self._ListItem()
            if inner_html is None:
                break
            cells.append(inner_html)
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
            inner_html = self._ListItem()
            if inner_html is None:
                break
            cells.append(inner_html)
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

        # Now write the table
        out.Print('<thead>\n')
        out.Print('<tr>\n')
        for cell in table['thead']:
            # TODO: parse <ulcol> and print attributes <td> attributes
            out.Print('  <td>')
            out.Print(cell)
            out.Print('</td>\n')
        out.Print('</tr>\n')
        out.Print('</thead>\n')

        for row in table['tr']:
            out.Print('<tr>\n')
            for cell in row:
                out.Print('  <td>')
                out.Print(cell)
                out.Print('</td>\n')
            out.Print('</tr>\n')

    out.PrintTheRest()

    return f.getvalue()
