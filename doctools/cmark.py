#!/usr/bin/env python2
"""Convert Markdown to HTML, with our enhancements

- Parse the HTML
- insert a TOC
- <pstrip> hack - this is obsolete with ul-table?
- Expand $xref links
- Highlight code blocks

I started from cmark-0.28.3/wrappers/wrapper.py.
"""
from __future__ import print_function

import ctypes
from typing import List
from typing import Tuple
from typing import Union
from typing import Optional
from typing import IO
from typing import Dict
try:
    from HTMLParser import HTMLParser
except ImportError:
    # python3
    from html.parser import HTMLParser  # type: ignore
import json
import optparse
import os
import pprint
import sys

from doctools import html_lib
from doctools import doc_html  # templates
from doctools import oils_doc
from doctools import ul_table
from lazylex import html as lazylex_html

if sys.version_info.major == 2:
    from typing import Any

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
cmark3 = '/wedge/oils-for-unix.org/pkg/cmark/0.29.0/lib/libcmark.so'  # a symlink

if cmark1 is not None and os.path.exists(cmark1):
    libname = cmark1
elif os.path.exists(cmark2):
    libname = cmark2
elif os.path.exists(cmark3):
    libname = cmark3
else:
    raise AssertionError("Couldn't find libcmark.so")

cmark = ctypes.CDLL(libname)

markdown = cmark.cmark_markdown_to_html
markdown.restype = ctypes.c_char_p
markdown.argtypes = [ctypes.c_char_p, ctypes.c_long, ctypes.c_long]


def log(msg, *args):
    # type: (str, Any) -> None
    if args:
        msg = msg % args

    if 0:
        print(msg, file=sys.stderr)


# Version 0.29.0 disallowed raw HTML by default!
CMARK_OPT_UNSAFE = (1 << 17)


def md2html(md):
    # type: (str) -> str
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


def demo():
    sys.stdout.write(md2html('*hi*'))


class TocExtractor(HTMLParser):
    """Extract Table of Contents

    When we hit h_tags (h2, h3, h4, etc.), append to self.headings, recording
    the line number.

    Later, we insert two things:
    - <a name=""> before each heading (may be obsolete, <h2 id=""> is OK)
    - The TOC after <div id="toc">
    """

    def __init__(self):
        # type: () -> None
        HTMLParser.__init__(self)

        # make targets for these, regardless of whether the TOC links to them.
        self.h_tags = ['h2', 'h3', 'h4']
        self.indent = 0

        # The TOC will be inserted after this.
        self.toc_begin_line = -1
        self.dense_toc_begin_line = -1

        self.capturing = False

        # Flat list of (line_num, tag, id, HTML)?
        # HTML is like innerHTML.  There can be <code> annotations and so forth.
        # id is optional -- it can be used for generating headings.
        self.headings = []

    def handle_starttag(self, tag, attrs):
        # type: (str, List[Tuple[str, str]]) -> None
        if tag == 'div':
            if attrs == [('id', 'toc')]:
                log('%s> %s %s', self.indent * '  ', tag, attrs)
                self.indent += 1
                self.toc_begin_line, _ = self.getpos()
            elif attrs == [('id', 'dense-toc')]:
                self.indent += 1
                self.dense_toc_begin_line, _ = self.getpos()

        # Can't have nested <a> tags
        if self.capturing and tag != 'a':
            self._AppendHtml('<%s%s>' % (tag, html_lib.AttrsToString(attrs)))

        if tag in self.h_tags:
            log('%s> %s %s', self.indent * '  ', tag, attrs)
            self.indent += 1
            line_num, _ = self.getpos()

            css_id = None
            for k, v in attrs:
                if k == 'id':
                    css_id = v
                    break
            self.headings.append((line_num, tag, css_id, [], []))
            self.capturing = True  # record the text inside <h2></h2> etc.

    def handle_endtag(self, tag):
        # type: (str) -> None
        # Debug print
        if tag == 'div':
            self.indent -= 1
            log('%s< %s', self.indent * '  ', tag)

        if tag in self.h_tags:
            self.indent -= 1
            log('%s< %s', self.indent * '  ', tag)
            self.capturing = False

        # Can't have nested <a> tags
        if self.capturing and tag != 'a':
            self._AppendHtml('</%s>' % tag)

    def handle_entityref(self, data):
        # type: (str) -> None
        """
        From Python docs:
        This method is called to process a named character reference of the form
        &name; (e.g. &gt;), where name is a general entity reference (e.g. 'gt').
        """
        # BUG FIX: For when we have say &quot; or &lt; in subheadings
        if self.capturing:
            self._AppendHtml('&%s;' % data)

    def handle_data(self, data):
        # type: (str) -> None
        # Debug print
        if self.indent > 0:
            log('%s| %r', self.indent * '  ', data)

        if self.capturing:
            self._AppendHtml(data)
            self._AppendText(data)

    def _AppendText(self, text):
        # type: (str) -> None
        """Accumulate text of the last heading."""
        _, _, _, _, text_parts = self.headings[-1]
        text_parts.append(text)

    def _AppendHtml(self, html):
        # type: (str) -> None
        """Accumulate HTML of the last heading."""
        _, _, _, html_parts, _ = self.headings[-1]
        html_parts.append(html)


TAG_TO_CSS = {'h2': 'toclevel1', 'h3': 'toclevel2', 'h4': 'toclevel3'}

# We could just add <h2 id="foo"> attribute!  I didn't know those are valid
# anchors.
# But it's easier to insert an entire line, rather than part ofa line.
ANCHOR_FMT = '<a name="%s"></a>\n'


def _MakeTocInsertions(
        opts,  # type: Any
        toc_tags,  # type: Union[List[str], Tuple[str, str]]
        headings,  # type: List[Tuple[int, str, None, List[str], List[str]]]
        toc_pos,  # type: int
        preserve_anchor_case,  # type: bool
):
    # type: (...) -> List[Tuple[int, str]]
    """Given extract headings list and TOC position, return a list of insertions.

    The insertions <div> for the TOC itself, and <a name=""> for the targets.

    Args:
      toc_tags: List of HTML tags ['h2', 'h3'] to SHOW in TOC.  But we LINK to
      all of them.
    """
    # Example:
    # <div class="toclevel2"><a href="#_toc_0">Introduction</a></div>
    #
    # Yeah it's just a flat list, and then indentation is done with CSS.  Hm
    # that's easy.

    toc_lines = ['<div id="toctitle">Table of Contents</div>\n']
    insertions = []

    i = 0
    for line_num, tag, css_id, html_parts, text_parts in headings:
        css_class = TAG_TO_CSS[tag]

        # Add BOTH href, for stability.
        numeric_href = 'toc_%d' % i

        # If there was an explicit CSS ID written by the user, use that as the href.
        # I used this in the blog a few times.

        pretty_href = html_lib.PrettyHref(
            ''.join(text_parts), preserve_anchor_case=preserve_anchor_case)

        if css_id:  # A FEW OLD BLOG POSTS USE an explicit CSS ID
            toc_href = css_id
        else:
            # Always use the pretty version now.  The old numeric version is still a
            # target, but not in the TOC.
            toc_href = pretty_href

        line = '  <div class="%s"><a href="#%s">%s</a></div>\n' % (
            css_class, toc_href, ''.join(html_parts))
        if tag in toc_tags:
            toc_lines.append(line)

        targets = []
        if opts.toc_pretty_href:  # NEW WAY
            targets.append(ANCHOR_FMT % pretty_href)
        elif css_id:  # Old blog explicit
            targets.append(ANCHOR_FMT % css_id)
            targets.append(ANCHOR_FMT % numeric_href)
        else:  # Old blog implicit
            targets.append(ANCHOR_FMT % pretty_href)  # Include the NEW WAY too
            targets.append(ANCHOR_FMT % numeric_href)

        insertions.append((line_num, ''.join(targets)))

        i += 1

    # +1 to insert AFTER the <div>
    toc_insert = (toc_pos + 1, ''.join(toc_lines))
    insertions.insert(0, toc_insert)  # The first insertion is TOC

    return insertions


def _MakeTocInsertionsDense(
        headings,  # type: List[Tuple[int, str, Optional[str], List[str], List[str]]]
        toc_pos,  # type: int
        preserve_anchor_case,  # type: bool
):
    # type: (...) -> List[Tuple[int, str]]
    """For the dense-toc style with columns, used by doc/ref

    The style above is simpler: it outputs a div for every line:

        <div id="toctitle">Table of Contents</div>

        <div class="toclevel1><a ...> Level 1 </a></div>
          <div class="toclevel2><a ...> 1.A </a></div>
          <div class="toclevel2><a ...> 1.B </a></div>
        <div class="toclevel1><a ...> Level 2 </a></div>
          ...

    We want something like this:

        <div id="dense-toc-title">Table of Contents</div>

        <div class="dense-toc-group"> 
          <a ...> Level 1 </a> <br/>

          <a class="dense-toc-h3" ...> 1.A </a> <br/>
          <a class="dense-toc-h3" ...> 1.B </a> <br/>

        </div>  # NO BREAKING within this div

        <div class="dense-toc-group"> 
          <a ...> Level 2 </a> <br/>
        </div>
    """

    heading_tree = []
    current_h2 = None

    insertions = []

    for line_num, tag, css_id, html_parts, text_parts in headings:

        pretty_href = html_lib.PrettyHref(
            ''.join(text_parts), preserve_anchor_case=preserve_anchor_case)

        if css_id:  # doc/ref can use <h3 id="explicit"></h3>
            toc_href = css_id
        else:
            # Always use the pretty version now.  The old numeric version is still a
            # target, but not in the TOC.
            toc_href = pretty_href

        anchor_html = ''.join(html_parts)

        # Create a two level tree
        if tag == 'h2':
            current_h2 = (anchor_html, toc_href, [])
            heading_tree.append(current_h2)
        elif tag == 'h3':
            assert current_h2 is not None, "h3 shouldn't come before any h2"
            current_h2[2].append((anchor_html, toc_href))

        # Insert the target <a name="">
        insertions.append((line_num, ANCHOR_FMT % pretty_href))

        #print('%d %s %s %s %s' % (line_num, tag, css_id, html_parts, text_parts))

    if 1:
        log('Heading Tree:')
        log(pprint.pformat(heading_tree))
        log('')

    toc_lines = ['<div id="dense-toc-title">In This Chapter</div>\n']
    toc_lines.append('<div id="dense-toc-cols">\n')

    for h2_html, h2_href, children in heading_tree:
        toc_lines.append('<div class="dense-toc-group">\n')
        toc_lines.append('  <a href="#%s">%s</a> <br/>\n' % (h2_href, h2_html))
        for h3_html, h3_href in children:
            toc_lines.append(
                '  <a class="dense-toc-h3" href="#%s">%s</a> <br/>\n' %
                (h3_href, h3_html))
        toc_lines.append('</div>\n')

    toc_lines.append('</div>\n')

    if 1:
        log('TOC lines')
        log(pprint.pformat(toc_lines))
        log('')

    # +1 to insert AFTER the <div>
    toc_insert = (toc_pos + 1, ''.join(toc_lines))
    insertions.insert(0, toc_insert)  # The first insertion is TOC

    return insertions


def _ApplyInsertions(lines, insertions, out_file):
    # type: (List[str], List[Tuple[int, str]], IO[str]) -> None
    assert insertions, "Should be at least one insertion"
    j = 0
    n = len(insertions)

    for i, line in enumerate(lines):
        current_line = i + 1  # 1-based

        if j < n:
            line_num, s = insertions[j]
            if current_line == line_num:
                out_file.write(s)
                j += 1

        out_file.write(line)


def Render(
        opts,  # type: Any
        meta,  # type: Dict
        in_file,  # type: IO[str]
        out_file,  # type: IO[str]
        use_fastlex=True,  # type: bool
        debug_out=None,  # type: Optional[Any]
):
    # type: (...) -> None
    if debug_out is None:
        debug_out = []

    # First convert to HTML
    html = md2html(in_file.read())
    #print(html, file=sys.stderr)

    # Now process HTML with oils_doc
    if use_fastlex:
        # Note: extract code BEFORE doing the HTML highlighting.
        if opts.code_block_output:
            with open(opts.code_block_output, 'w') as f:
                f.write('# %s: code blocks extracted from Markdown/HTML\n\n' %
                        opts.code_block_output)
                text = oils_doc.ExtractCode(html, f)

        html = ul_table.RemoveComments(html)

        # Hack for allowing tables without <p> in cells, which CommonMark seems
        # to require?
        html = html.replace('<p><pstrip>', '')
        html = html.replace('</pstrip></p>', '')

        try:
            html = ul_table.ReplaceTables(html)
        except lazylex_html.ParseError as e:
            print('Error rendering file %r' % in_file, file=sys.stderr)
            raise

        # Expand $xref, etc.
        html = oils_doc.ExpandLinks(html)

        # <code> blocks
        # Including class=language-oil-help-topics
        html = oils_doc.HighlightCode(html,
                                      meta.get('default_highlighter'),
                                      debug_out=debug_out)

    # h2 is the title.  h1 is unused.
    if opts.toc_tags:
        toc_tags = opts.toc_tags
    else:
        toc_tags = ('h3', 'h4')

    parser = TocExtractor()
    parser.feed(html)

    log('')
    log('*** HTML headings:')
    for heading in parser.headings:
        log(heading)

    preserve_anchor_case = bool(meta.get('preserve_anchor_case', ''))

    if parser.toc_begin_line != -1:
        insertions = _MakeTocInsertions(opts, toc_tags, parser.headings,
                                        parser.toc_begin_line,
                                        preserve_anchor_case)
    elif parser.dense_toc_begin_line != -1:
        insertions = _MakeTocInsertionsDense(parser.headings,
                                             parser.dense_toc_begin_line,
                                             preserve_anchor_case)
    else:  # No TOC found Not found!
        out_file.write(html)  # Pass through
        return

    log('')
    log('*** Text Insertions:')
    for ins in insertions:
        log(ins)

    log('')
    log('*** Output:')

    lines = html.splitlines(True)  # keep newlines
    _ApplyInsertions(lines, insertions, out_file)


def Options():
    # type: () -> Any
    p = optparse.OptionParser('cmark.py [options]')

    p.add_option('--common-mark',
                 action='store_true',
                 default=False,
                 help='Only do CommonMark conversion')

    p.add_option(
        '--toc-pretty-href',
        action='store_true',
        default=False,
        help='Generate textual hrefs #like-this rather than like #toc10')
    p.add_option('--toc-tag',
                 dest='toc_tags',
                 action='append',
                 default=[],
                 help='h tags to include in the TOC, e.g. h2 h3')
    p.add_option('--disable-fastlex',
                 dest='disable_fastlex',
                 action='store_true',
                 default=False,
                 help='Hack for old blog posts')

    p.add_option('--code-block-output',
                 dest='code_block_output',
                 default=None,
                 help='Extract and print code blocks to this file')

    return p


# width 40 by default
DEFAULT_META = {'body_css_class': 'width40'}


def main(argv):
    o = Options()
    opts, argv = o.parse_args(argv)
    assert all(tag.startswith('h') for tag in opts.toc_tags), opts.toc_tags

    if opts.common_mark:
        print(md2html(sys.stdin.read()))
        return

    meta = dict(DEFAULT_META)

    if len(argv) == 3:  # It's Oils documentation
        with open(argv[1]) as f:
            meta.update(json.load(f))

        # Docs have a special header and footer.
        with open(argv[2]) as content_f:
            doc_html.Header(meta, sys.stdout, draft_warning=True)
            Render(opts, meta, content_f, sys.stdout)
            doc_html.Footer(meta, sys.stdout)
    else:
        # Filter for blog and for benchmarks.

        # Metadata is optional here
        try:
            with open(argv[1]) as f:
                meta.update(json.load(f))
        except IndexError:
            pass

        # Old style for blog: it's a filter
        Render(opts,
               meta,
               sys.stdin,
               sys.stdout,
               use_fastlex=not opts.disable_fastlex)


if __name__ == '__main__':
    main(sys.argv)
