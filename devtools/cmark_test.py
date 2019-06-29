#!/usr/bin/python -S
"""
cmark_test.py: Tests for cmark.py
"""

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

class RenderTest(unittest.TestCase):

  def testRender(self):
    out_file = cStringIO.StringIO()
    cmark.Render(SIMPLE_DOC, out_file)
    self.assertEqual('<p>hi</p>\n', out_file.getvalue())

    out_file = cStringIO.StringIO()
    cmark.Render(TOC_DOC, out_file)
    print out_file.getvalue()


if __name__ == '__main__':
  unittest.main()
