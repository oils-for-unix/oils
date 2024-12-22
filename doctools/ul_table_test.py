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
  - <ulcol class="foo" /> name
  - <ulcol class="bar" /> [age](https://example.com/)
- tr
  - alice *italic*
  - 30
- tr
  - bob
  - 42

</table>"""  # no extra

TEST2 = """
<table>

- ul-head
  - <ulcol id="foo" /> arbitrary text
  - age
- ul-row
  - alice
  - 30
- <ulrow id="spam" />  # a way to attach attributes
  - bob
  - 42

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
        self.assertEqual(
            """\
<table>
<thead>
<tr>
  <td><em>name</em></td>
  <td><em>age</em></td>
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
- tr
  - 1
  - 2
- tr
  - wrong number of cells
- tr
  - 3
  - 4
""")
        except html.ParseError as e:
            print(e)
        else:
            self.fail('Expected parse error')


if __name__ == '__main__':
    unittest.main()
