#!/usr/bin/env python2
"""cmark_test.py: Tests for cmark.py."""
from __future__ import print_function

import cStringIO
import os
import sys
import unittest
from pprint import pprint

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

NEW_DOC = """
Title
=====

<div id="toc">
</div>

## One

hello h2.

### subheading `backticks`

hello H3.

#### subsubheading

This kind of heading gets an h4.  It's not in the TOC, but it can be linked to.

## Two &amp; Three

"""

DOC_WITH_METADATA = cStringIO.StringIO("""
- repo-url: doc/README.md

Title
=====

## One
""")

_HTML_1 = '''
<p>dummy
</p>

<div id="toc">
</div>

<h2>One <a href="/">link</a></h2>

hello one.

<h3>subheading <code>backticks</code></h3>

<h3>one &amp; two</h3>

<h2 id="explicit">Two</h2>

'''


class RenderTest(unittest.TestCase):

    def testRender(self):
        # type: () -> None
        opts, _ = cmark.Options().parse_args([])

        out_file = cStringIO.StringIO()
        cmark.Render(opts, {}, SIMPLE_DOC, out_file)
        self.assertEqual('<p>hi</p>\n', out_file.getvalue())

        out_file = cStringIO.StringIO()
        cmark.Render(opts, {}, TOC_DOC, out_file)
        print(out_file.getvalue())

    def testNewRender(self):
        # type: () -> None
        # New style of doc

        new_flags = ['--toc-tag', 'h2', '--toc-tag', 'h3']
        opts, _ = cmark.Options().parse_args(new_flags)

        in_file = cStringIO.StringIO(NEW_DOC)
        out_file = cStringIO.StringIO()
        cmark.Render(opts, {}, in_file, out_file)

        h = out_file.getvalue()
        self.assert_('<div class="toclevel1"><a href="#one">' in h, h)

    def testNewPrettyHref(self):
        # type: () -> None
        # New style of doc

        new_flags = ['--toc-tag', 'h2', '--toc-tag', 'h3', '--toc-pretty-href']
        opts, _ = cmark.Options().parse_args(new_flags)

        in_file = cStringIO.StringIO(NEW_DOC)
        out_file = cStringIO.StringIO()
        cmark.Render(opts, {}, in_file, out_file)
        h = out_file.getvalue()
        self.assert_('<a name="subsubheading">' in h, h)

        self.assert_('<div class="toclevel1"><a href="#one">' in h, h)
        print(h)

    def testExtractor(self):
        # type: () -> None
        parser = cmark.TocExtractor()
        parser.feed(_HTML_1)
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

    def testExtractorDense(self):
        # type: () -> None
        parser = cmark.TocExtractor()
        parser.feed(_HTML_1.replace('"toc"', '"dense-toc"'))

        self.assertEqual(-1, parser.toc_begin_line)
        self.assertEqual(5, parser.dense_toc_begin_line)

        insertions = cmark._MakeTocInsertionsDense(parser.headings,
                                                   parser.dense_toc_begin_line,
                                                   True)
        pprint(insertions)


def InitCMark():
    import ctypes

    # Geez find_library returns the filename and not the path?  Just hardcode it as
    # a workaround.
    # https://bugs.python.org/issue21042

    #from ctypes.util import find_library
    #libname = find_library("cmark")
    #assert libname, "cmark not found"

    # There's some ongoing discussion about how to deal with the same in Nix.
    # I think normally you'd just patch/substitute this path during the Nix build.
    # See note in shell.nix
    this_dir = os.path.abspath(os.path.dirname(sys.argv[0]))

    cmark1 = os.environ.get('_NIX_SHELL_LIBCMARK')
    cmark2 = os.path.join(this_dir, '../../oil_DEPS/libcmark.so')
    cmark3 = os.path.join(cmark.CMARK_WEDGE_DIR,
                          'lib/libcmark.so')  # a symlink

    if cmark1 is not None and os.path.exists(cmark1):
        libname = cmark1
    elif os.path.exists(cmark2):
        libname = cmark2
    elif os.path.exists(cmark3):
        libname = cmark3
    else:
        raise AssertionError("Couldn't find libcmark.so")

    cmark_dll = ctypes.CDLL(libname)

    markdown = cmark_dll.cmark_markdown_to_html
    markdown.restype = ctypes.c_char_p
    markdown.argtypes = [ctypes.c_char_p, ctypes.c_long, ctypes.c_long]
    return markdown


# Version 0.29.0 disallowed raw HTML by default!
CMARK_OPT_UNSAFE = (1 << 17)


def md2html(md):
    # type: (str) -> str
    markdown = InitCMark()

    if sys.version_info.major == 2:
        md_bytes = md
    else:
        md_bytes = md.encode('utf-8')

    md_len = len(md)
    html = markdown(md_bytes, md_len, CMARK_OPT_UNSAFE)

    if sys.version_info.major == 2:
        return html
    else:
        return html.decode('utf-8')


class CompareTest(unittest.TestCase):
    """Test that the child process behaves like the shared library"""

    def OLD_testChildProcess(self):
        # OK it adds a newline
        md = '*hi*'
        h = md2html(md)
        print(repr(h))

        h2 = cmark.cmark_bin(md)
        print(repr(h2))

        self.assertEqual(h, h2)

    def OLD_testHtml(self):
        md2 = '*hi* <script>alert("hi");</script>'
        h = md2html(md2)
        print(repr(h))

        # OK this omits the HTML, which we need
        h2 = cmark.cmark_bin(md2)
        print(repr(h2))

        self.assertEqual(h, h2)


if __name__ == '__main__':
    unittest.main()
