#!/usr/bin/python -S
"""
cmark_test.py: Tests for cmark.py
"""
from __future__ import print_function

import cStringIO
import unittest

import cmark  # module under test

# No TOC!
SIMPLE_DOC = cStringIO.StringIO("""
hi
""")

TOC_DOC = cStringIO.StringIO("""
Title
-----

<div id="toc">
</div>

### Intro

This is an h3
in the intro.

### Part One: <code>bash</code>

Another h3.

#### Detail 1 with <a href="foo.html?a=1&b=2">link</a>

An h4.

<h4 id="detail2">Detail 2</h4>

Another h4.

### Conclusion

Concluding h3.

<!-- The blank lines here show a problem that is papered over by fill-blank-lines
     in Snip -->
<div class="highlight"><pre><span></span>
def f():
  if 0:
    return False

  if 0:
    return True
</pre></div>
""")

NEW_DOC = cStringIO.StringIO("""
Title
=====

<div id="toc">
</div>

## One

hello one.

### subheading `backticks`

## Two &amp; Three

""")


DOC_WITH_METADATA = cStringIO.StringIO("""
- repo-url: doc/README.md

Title
=====

## One
""")


class RenderTest(unittest.TestCase):

  def testRender(self):
    opts, _ = cmark.Options().parse_args([])

    out_file = cStringIO.StringIO()
    cmark.Render(opts, SIMPLE_DOC, out_file)
    self.assertEqual('<p>hi</p>\n', out_file.getvalue())

    out_file = cStringIO.StringIO()
    cmark.Render(opts, TOC_DOC, out_file)
    print(out_file.getvalue())

  def testNewRender(self):
    # New style of doc

    new_flags = ['--toc-tag', 'h2', '--toc-tag', 'h3']
    opts, _ = cmark.Options().parse_args(new_flags)

    out_file = cStringIO.StringIO()
    cmark.Render(opts, NEW_DOC, out_file)
    print(out_file.getvalue())

  def testExtractor(self):
    toc_tags = ['h2', 'h3']
    parser = cmark.TocExtractor(toc_tags)
    parser.feed('''
<p>dummy
</p>

<div id="toc">
</div>

<h2>One <a href="/">link</a></h2>

hello one.

<h3>subheading <code>backticks</code></h3>

<h3>one &amp; two</h3>

<h2 id="explicit">Two</h2>

''')

    self.assertEqual(5, parser.toc_begin_line)

    for heading in parser.headings:
      print(heading)

    headings = parser.headings
    self.assertEqual(4, len(headings))

    line_num, tag, css_id, html, text = headings[0]
    self.assertEqual(8, line_num)
    self.assertEqual('h2', tag)
    self.assertEqual(None, css_id)
    # nested <a> tags are omitted!
    self.assertEqual('One link', ''.join(html))
    self.assertEqual('One link', ''.join(text))

    line_num, tag, css_id, html, text = headings[1]
    self.assertEqual(12, line_num)
    self.assertEqual('h3', tag)
    self.assertEqual(None, css_id)
    self.assertEqual('subheading <code>backticks</code>', ''.join(html))
    self.assertEqual('subheading backticks', ''.join(text))

    line_num, tag, css_id, html, text = headings[2]
    self.assertEqual(14, line_num)
    self.assertEqual('h3', tag)
    self.assertEqual(None, css_id)
    self.assertEqual('one &amp; two', ''.join(html))
    self.assertEqual('one  two', ''.join(text))

    line_num, tag, css_id, html, text = headings[3]
    self.assertEqual(16, line_num)
    self.assertEqual('h2', tag)
    self.assertEqual('explicit', css_id)
    self.assertEqual('Two', ''.join(html))
    self.assertEqual('Two', ''.join(text))


class FunctionsTest(unittest.TestCase):

  def testPrettyHref(self):
    self.assertEqual('foo-bar', cmark.PrettyHref('foo  bar'))
    self.assertEqual('why-not', cmark.PrettyHref('Why Not??'))
    self.assertEqual('cant-touch-this', cmark.PrettyHref("Can't Touch This!"))
    # This is what github does:
    if 0:
      self.assertEqual('section-2--3', cmark.PrettyHref("Section 2 + 3"))
      self.assertEqual('break--return--continue', cmark.PrettyHref("break / return / continue"))
      self.assertEqual('inside-', cmark.PrettyHref('Inside ${}'))
    # Ours is cleaner
    else:
      self.assertEqual('section-2-3', cmark.PrettyHref("Section 2 + 3"))
      self.assertEqual('break-return-continue', cmark.PrettyHref("break / return / continue"))
      self.assertEqual('inside', cmark.PrettyHref('Inside ${}'))
      self.assertEqual('bash-compatible', cmark.PrettyHref('Bash-Compatible'))


if __name__ == '__main__':
  unittest.main()
