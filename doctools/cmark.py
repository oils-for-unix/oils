#!/usr/bin/env python2
"""
Convert markdown to HTML, then parse the HTML, generate and insert a TOC, and
insert anchors.

I started from cmark-0.28.3/wrappers/wrapper.py.
"""
from __future__ import print_function

import ctypes
import HTMLParser
import optparse
import os
import re
import sys

from doctools  import html_lib
from doctools import doc_html  # templates
from doctools import oil_doc

# Geez find_library returns the filename and not the path?  Just hardcode it as
# a workaround.
# https://bugs.python.org/issue21042

#from ctypes.util import find_library
#libname = find_library("cmark")
#assert libname, "cmark not found"

libname = '/usr/local/lib/libcmark.so'

cmark = ctypes.CDLL(libname)

markdown = cmark.cmark_markdown_to_html
markdown.restype = ctypes.c_char_p
markdown.argtypes = [ctypes.c_char_p, ctypes.c_long, ctypes.c_long]


def log(msg, *args):
  if args:
    msg = msg % args

  # Uncomment to debug
  #print(msg, file=sys.stderr)


# Version 0.29.0 disallowed raw HTML by default!
CMARK_OPT_UNSAFE = (1 << 17)

def md2html(text):
  textbytes = text
  textlen = len(text)
  return markdown(textbytes, textlen, CMARK_OPT_UNSAFE)


def demo():
  sys.stdout.write(md2html('*hi*'))


def PrettyHref(s):
  """
  Turn arbitrary heading text into a clickable href with no special characters.

  This is modelled after what github does.  It makes everything lower case.
  """
  # Split by whitespace or hyphen
  words = re.split(r'[\s\-]+', s)

  # Keep only alphanumeric
  keep = [''.join(re.findall(r'\w+', w)) for w in words]

  # Join with - and lowercase.  And then remove empty words, unlike Github.
  # This is SIMILAR to what Github does, but there's no need to be 100%
  # compatible.
  return '-'.join(p.lower() for p in keep if p)


class TocExtractor(HTMLParser.HTMLParser):
  """
  When he hit h_tags (h2, h3, h4, etc.), append to self.headings, recording the
  line number.

  Later, we insert two things:
  - <a name=""> before each heading
  - The TOC after <div id="toc">
  """
  def __init__(self, h_tags):
    HTMLParser.HTMLParser.__init__(self)
    self.h_tags = h_tags
    self.indent = 0

    # The TOC will be inserted after this.
    self.toc_begin_line = -1
    self.capturing = False

    # Flat list of (line_num, tag, id, HTML)?
    # HTML is like innerHTML.  There can be <code> annotations and so forth.
    # id is optional -- it can be used for generating headings.
    self.headings = []

  def handle_starttag(self, tag, attrs):
    if tag == 'div' and attrs == [('id', 'toc')]:
      log('%s> %s %s', self.indent * '  ', tag, attrs)
      self.indent += 1
      self.toc_begin_line, _ = self.getpos()

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
    """
    From Python docs:
    This method is called to process a named character reference of the form
    &name; (e.g. &gt;), where name is a general entity reference (e.g. 'gt').
    """
    # BUG FIX: For when we have say &quot; or &lt; in subheadings
    if self.capturing:
      self._AppendHtml('&%s;' % data)

  def handle_data(self, data):
    # Debug print
    if self.indent > 0:
      log('%s| %r', self.indent * '  ', data)

    if self.capturing:
      self._AppendHtml(data)
      self._AppendText(data)

  def _AppendText(self, text):
    """Accumlate text of the last heading."""
    _, _, _, _, text_parts = self.headings[-1]
    text_parts.append(text)

  def _AppendHtml(self, html):
    """Accumulate HTML of the last heading."""
    _, _, _, html_parts, _ = self.headings[-1]
    html_parts.append(html)


TAG_TO_CSS = {'h2': 'toclevel1', 'h3': 'toclevel2', 'h4': 'toclevel3'}


def _MakeTocAndAnchors(opts, headings, toc_pos):
  """
  Given a list of extract headings and TOC position, render HTML to insert.
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

    pretty_href = PrettyHref(''.join(text_parts))

    if css_id:              # A FEW OLD BLOG POSTS USE an explicit CSS ID
      toc_href = css_id
    else:
      # Always use the pretty version now.  The old numeric version is still a
      # target, but not in the TOC.
      toc_href = pretty_href

    line = '  <div class="%s"><a href="#%s">%s</a></div>\n' % (
        css_class, toc_href, ''.join(html_parts))
    toc_lines.append(line)

    FMT = '<a name="%s"></a>\n'

    targets = []
    if opts.toc_pretty_href:  # NEW WAY
      targets.append(FMT % pretty_href)
    elif css_id:              # Old blog explicit
      targets.append(FMT % css_id)
      targets.append(FMT % numeric_href)
    else:                     # Old blog implicit
      targets.append(FMT % pretty_href)  # Include the NEW WAY too
      targets.append(FMT % numeric_href)

    insertions.append((line_num, ''.join(targets)))

    i += 1

  # +1 to insert AFTER the <div>
  toc_insert = (toc_pos+1, ''.join(toc_lines))
  insertions.insert(0, toc_insert)  # The first insertion is TOC

  return insertions


def _ApplyInsertions(lines, insertions, out_file):
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


def Render(opts, in_file, out_file, use_fastlex=True):
  html = md2html(in_file.read())

  if use_fastlex:
    html = oil_doc.RemoveComments(html)

    # Hack for allowing tables without <p> in cells, which CommonMark seems to require?
    html = html.replace('<p><pstrip>', '')
    html = html.replace('</pstrip></p>', '')

    # Stages of transformation.
    html = oil_doc.ExpandLinks(html)

    html = oil_doc.HighlightCode(html)

  # h2 is the title.  h1 is unused.
  if opts.toc_tags:
    toc_tags = opts.toc_tags
  else:
    toc_tags = ('h3', 'h4')

  parser = TocExtractor(toc_tags)
  parser.feed(html)

  log('')
  log('*** HTML headings:')
  for heading in parser.headings:
    log(heading)

  if parser.toc_begin_line == -1:  # Not found!
    out_file.write(html)  # Pass through
    return

  insertions = _MakeTocAndAnchors(opts, parser.headings, parser.toc_begin_line)

  log('')
  log('*** Text Insertions:')
  for ins in insertions:
    log(ins)

  log('')
  log('*** Output:')

  lines = html.splitlines(True)  # keep newlines
  _ApplyInsertions(lines, insertions, out_file)


def Options():
  """Returns an option parser instance."""
  p = optparse.OptionParser('cmark.py [options]')
  p.add_option(
      '--toc-pretty-href', action='store_true', default=False,
      help='Generate textual hrefs #like-this rather than like #toc10')
  p.add_option(
      '--toc-tag', dest='toc_tags', action='append', default=[],
      help='h tags to include in the TOC, e.g. h2 h3')
  p.add_option(
      '--disable-fastlex', dest='disable_fastlex', action='store_true',
      default=False,
      help='Hack for old blog posts')
  return p


# width 40 by default
DEFAULT_META = {
    'body_css_class': 'width40'
}


def main(argv):
  o = Options()
  opts, argv = o.parse_args(argv)
  assert all(tag.startswith('h') for tag in opts.toc_tags), opts.toc_tags

  if len(argv) == 1:
    # Old style for blog: it's a filter
    Render(opts, sys.stdin, sys.stdout, use_fastlex=not opts.disable_fastlex)
    return

  # Otherwise we expect metadata and content

  meta = dict(DEFAULT_META)
  import json
  with open(argv[1]) as f:
    doc_meta = json.load(f)
  meta.update(doc_meta)

  with open(argv[2]) as content_f:
    doc_html.Header(meta, sys.stdout)
    Render(opts, content_f, sys.stdout)
    doc_html.Footer(meta, sys.stdout)


if __name__ == '__main__':
  main(sys.argv)
