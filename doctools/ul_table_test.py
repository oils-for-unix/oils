#!/usr/bin/env python2
from __future__ import print_function

import cmark  # Oils dev dependency

import unittest

from lazylex import html
from doctools import ul_table

# <ulcol> is a special annotation
TEST1 = """\
<table id="foo">

- thead 
  - <cell-attrs class="foo" /> name
  - <cell-attrs class="bar" /> [age](https://example.com/)
- tr
  - alice *italic*
  - 30
- tr
  - bob
  - 42

</table>"""  # no extra

TD_ATTRS = """\
<table>

- thead
  - <cell-attrs class=unquoted /> name
  - <cell-attrs class=quoted /> age
  - role
- tr
  - <cell-attrs class="cool" /> alice
  - 30
  - parent
- tr
  - bob
  - 42
  - <cell-attrs class=child /> child

</table>
"""

TD_ATTRS_HTML = """\
<table>
<thead>
<tr>
  <th> name</th>
  <th> age</th>
  <th>role</th>
</tr>
</thead>
<tr>
  <td class="unquoted cool"> alice</td>
  <td class="quoted">30</td>
  <td>parent</td>
</tr>
<tr>
  <td class="unquoted">bob</td>
  <td class="quoted">42</td>
  <td class="child"> child</td>
</tr>
</table>
"""

TRAILING_ATTRS = """\
<table>

- thead
  - OSH
  - YSH
- tr
  - ```
    echo osh
    ```
    <cell-attrs class=osh-code />
  - ```
    echo ysh
    ```
    <cell-attrs class=ysh-code />

</table>
"""

TRAILING_ATTRS_HTML = """\
<table>
<thead>
<tr>
  <th>OSH</th>
  <th>YSH</th>
</tr>
</thead>
<tr>
  <td class="osh-code">
<pre><code>echo osh
</code></pre>

</td>
  <td class="ysh-code">
<pre><code>echo ysh
</code></pre>

</td>
</tr>
</table>
"""

TR_ATTRS = """\
<table>

- thead
  - <cell-attrs class=unquoted /> name
  - <cell-attrs class=quoted /> age
  - role
- tr   <row-attrs class=totals />
  - alice
  - 30
  - parent
- tr
  - bob
  - 42
  - <cell-attrs class=child /> child

</table>
"""

TR_ATTRS_HTML = """\
<table>
<thead>
<tr>
  <th> name</th>
  <th> age</th>
  <th>role</th>
</tr>
</thead>
<tr class="totals">
  <td class="unquoted">alice</td>
  <td class="quoted">30</td>
  <td>parent</td>
</tr>
<tr>
  <td class="unquoted">bob</td>
  <td class="quoted">42</td>
  <td class="child"> child</td>
</tr>
</table>
"""

# Note CSS Grid can express colspan
# https://developer.mozilla.org/en-US/docs/Web/CSS/grid-column

COLSPAN = """\
<table>

- thead
  - <cell-attrs class=foo /> name
  - age
- tr
  - alice
  - 30
- tr
  - <cell-attrs colspan=2 /> ... more ...
- tr
  - bob
  - 42

</table>
"""

COLSPAN_HTML = """\
<table>
<thead>
<tr>
  <th> name</th>
  <th>age</th>
</tr>
</thead>
<tr>
  <td class="foo">alice</td>
  <td>30</td>
</tr>
<tr>
  <td class="foo" colspan="2"> ... more ...</td>
</tr>
<tr>
  <td class="foo">bob</td>
  <td>42</td>
</tr>
</table>
"""

# UNUSED - not worth it now
MIXED_TR = """\
<table>

- thead
  - name
  - age
- tr
  - 30
  - parent

<tr>
  <td colspan=2> - </td>
</tr>

- tr
  - bob
  - 42
  - <cell-attrs class=child /> child

</table>
"""


def MarkdownToTable(md):
    # markdown -> HTML

    h = cmark.md2html(md)
    # Markdown adds a newline
    if h.endswith('\n'):
        print('ENDS WITH NEWLINE %r' % h[-10:])

    if 1:
        print('---')
        print('ORIGINAL')
        print(h)
        print('')

    h2 = ul_table.ReplaceTables(h)

    if 1:
        print('---')
        print('REPLACED')
        print(h2)
        print('')

    return h2


class UlTableTest(unittest.TestCase):

    def testOne(self):
        h = MarkdownToTable('hi\n' + TEST1 + '\n\n bye \n')

    def testNoHeader(self):
        # HTML looks like:
        #
        # <table>
        #   <ul>  # problem: we need to lookahead SPACE <li> (tr or thead)
        #     <li>tr
        #       <ul>
        #          <li>one</li>
        #       </ul>
        #     </li>
        #   </ul>
        # </table>

        h = MarkdownToTable('''\
<table>

- tr
  - one                             
  - two

</table>
''')
        print(h)

    def testSimple(self):
        h = MarkdownToTable("""\
<table>

- thead
  - *name*
  - *age*
- tr
  - alice
  - 30
- tr
  - bob
  - 40

<table>
""")
        self.assertMultiLineEqual(
            """\
<table>
<thead>
<tr>
  <th><em>name</em></th>
  <th><em>age</em></th>
</tr>
</thead>
<tr>
  <td>alice</td>
  <td>30</td>
</tr>
<tr>
  <td>bob</td>
  <td>40</td>
</tr>
<table>
""", h)

    def testMultipleTables(self):
        # They can be right next to each other
        html_one = MarkdownToTable(TEST1)

        self.assert_(not TEST1.endswith('\n'))
        # CommonMark added a newline
        self.assert_(html_one.endswith('\n'))
        html_one = html_one[:-1]

        html_two = MarkdownToTable(TEST1 + TEST1)

        # The output is just concatenated
        self.assertMultiLineEqual(html_one + html_one + '\n', html_two)

    def testMultipleTablesWithSpace(self):
        h = MarkdownToTable(TEST1 + '\n\n hi \n' + TEST1)

    def testTdAttrs(self):
        h = MarkdownToTable(TD_ATTRS)
        self.assertMultiLineEqual(TD_ATTRS_HTML, h)

    def testTdAttrsTrailing(self):
        self.maxDiff = 2000
        h = MarkdownToTable(TRAILING_ATTRS)
        if 1:
            print('expect', repr(TRAILING_ATTRS_HTML))
            print('actual', repr(h))
        self.assertMultiLineEqual(TRAILING_ATTRS_HTML, h)

    def testColspan(self):
        h = MarkdownToTable(COLSPAN)
        self.assertMultiLineEqual(COLSPAN_HTML, h)

    def testTrAttrs(self):
        h = MarkdownToTable(TR_ATTRS)
        self.assertMultiLineEqual(TR_ATTRS_HTML, h)

    def testMixedTr(self):
        # Not worth it
        return
        h = MarkdownToTable(MIXED_TR)
        #self.assertMultiLineEqual(MIXED_TR, h)

    def testSyntaxErrors(self):
        # Once we get <table><ul>, then we TAKE OVER, and start being STRICT

        try:
            h = MarkdownToTable("""
<table>

- should be thead
  - one
  - two
""")
        except html.ParseError as e:
            print(e)
        else:
            self.fail('Expected parse error')

        try:
            h = MarkdownToTable("""
<table>

- thead
  - one
  - two
- tr <bad-attrs />
  - 1
  - 2
""")
        except html.ParseError as e:
            print(e)
        else:
            self.fail('Expected parse error')

    def testColumnCheck(self):
        # Disabled because of colspan
        return

        try:
            h = MarkdownToTable("""
<table>

- thead
  - one
  - two
- tr
  - 1
  - 2
- tr
  - wrong number of cells
- tr
  - 3
  - 4

</table>
""")
        except html.ParseError as e:
            print(e)
        else:
            self.fail('Expected parse error')


if __name__ == '__main__':
    unittest.main()
