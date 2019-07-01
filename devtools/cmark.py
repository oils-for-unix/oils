#!/usr/bin/env python
"""
Convert markdown to HTML, then parse the HTML, generate and insert a TOC, and
insert anchors.

I started from cmark-0.28.3/wrappers/wrapper.py.
"""
from __future__ import print_function

import ctypes
import sys

import cgi
import HTMLParser

# Geez find_library returns the filename and not the path?  Just hardcode it as
# a workaround.
# https://bugs.python.org/issue21042

#from ctypes.util import find_library
#libname = find_library("cmark")
#assert libname, "cmark not found"

libname = '/usr/local/lib/libcmark.so'
cmark = ctypes.CDLL(libname)
#print dir(cmark)

markdown = cmark.cmark_markdown_to_html
markdown.restype = ctypes.c_char_p
markdown.argtypes = [ctypes.c_char_p, ctypes.c_long, ctypes.c_long]


def log(msg, *args):
  if args:
    msg = msg % args

  # Uncomment to debug
  #print >>sys.stderr, msg


CMARK_OPTS = 0 # defaults

def md2html(text):
  textbytes = text
  textlen = len(text)
  return markdown(textbytes, textlen, CMARK_OPTS)


def demo():
  sys.stdout.write(md2html('*hi*'))


# h2 is the title.  h1 is unused.
H_TAGS = ('h3', 'h4')

class TocExtractor(HTMLParser.HTMLParser):
  """
  Look for.

  <div id="toc">
  """
  def __init__(self):
    HTMLParser.HTMLParser.__init__(self)
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

    if self.capturing:
      # Hm it's a little lame we have to reconstruct the HTML?
      if attrs:
        attr_html = ' '.join(
            '%s="%s"' % (k, cgi.escape(v, quote=True)) for (k, v) in attrs)
        self._AppendHtml('<%s %s>' % (tag, attr_html))
      else:
        self._AppendHtml('<%s>' % tag)

    if tag in H_TAGS:
      log('%s> %s %s', self.indent * '  ', tag, attrs)
      self.indent += 1
      line_num, _ = self.getpos()

      css_id = None
      for k, v in attrs:
        if k == 'id':
          css_id = v
          break
      self.headings.append((line_num, tag, css_id, []))
      self.capturing = True

  def handle_endtag(self, tag):
    # Debug print
    if tag == 'div':
      self.indent -= 1
      log('%s< %s', self.indent * '  ', tag)

    if tag in H_TAGS:
      self.indent -= 1
      log('%s< %s', self.indent * '  ', tag)
      self.capturing = False

    if self.capturing:
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

  def _AppendHtml(self, html):
    _, _, _, html_parts = self.headings[-1]
    html_parts.append(html)


def _MakeTocAndAnchors(headings, toc_pos):
  """
  Given a list of extract headings and TOC position, render HTML to insert.
  """
  # Example:
  # <div class="toclevel2"><a href="#_toc_0">Introduction</a></div>
  #
  # Yeah it's just a flat list, and then indentation is done with CSS.  Hm
  # that's easy.

  toc_lines = ['<div id="toctitle">Table of Contents</div>']
  insertions = []

  i = 0
  for line_num, tag, css_id, html_parts in headings:
    css_class = {'h3': 'toclevel2', 'h4': 'toclevel3'}[tag]

    # Add BOTH anchors, for stability.
    numeric_anchor = 'toc_%d' % i
    href = css_id or numeric_anchor

    line = '<div class="%s"><a href="#%s">%s</a></div>\n' % (
        css_class, href, ''.join(html_parts))
    toc_lines.append(line)

    target = '<a name="%s"></a>\n' % numeric_anchor
    if css_id:
      target += '<a name="%s"></a>\n' % css_id
    insertions.append((line_num, target))

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


def Render(in_file, out_file):
  html = md2html(in_file.read())

  parser = TocExtractor()
  parser.feed(html)

  log('')
  log('*** HTML headings:')
  for heading in parser.headings:
    log(heading)

  if parser.toc_begin_line == -1:  # Not found!
    out_file.write(html)  # Pass through
    return

  insertions = _MakeTocAndAnchors(parser.headings, parser.toc_begin_line)

  log('')
  log('*** Text Insertions:')
  for ins in insertions:
    log(ins)

  log('')
  log('*** Output:')

  lines = html.splitlines(True)  # keep newlines
  _ApplyInsertions(lines, insertions, out_file)


def main(argv):
  Render(sys.stdin, sys.stdout)


if __name__ == '__main__':
  main(sys.argv)
