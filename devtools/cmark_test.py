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

### subheading

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


if __name__ == '__main__':
  unittest.main()
