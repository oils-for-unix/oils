#!/usr/bin/env python2
"""
oil_doc.py: HTML processing for Oil documentation.
"""
from __future__ import print_function

import cgi
import cStringIO
import re
import sys

from lazylex import html

log = html.log

_REPLACEMENTS = [
  ('$xref:', '/cross-ref.html?tag=%(value)s#%(value)s'),
  ('$blog-tag:', '/blog/tags.html?tag=%(value)s#%(value)s'),
]

TAG_RE = re.compile(r'href= "? ([^ >"]*) "?', re.VERBOSE)

def ExpandLinks(s):
  """
  Expand $xref:bash and so forth
  """
  f = cStringIO.StringIO()
  out = html.Output(s, f)

  tag_lexer = html.TagLexer()

  start_pos = 0

  # for tok_id, end_pos in html.Tokens
  for tok_id, end_pos in html.Tokens(s):
    #log('%s', event)

    if tok_id ==  html.StartTag:
      # TODO: Change this to 
      # GetTag(s, p.StartPos())

      tag_lexer.Reset(s, start_pos, end_pos)
      if tag_lexer.Tag() == 'a':
        out.PrintUntil(start_pos)

        href_start, href_end = tag_lexer.GetSpanForAttrValue('href')
        if href_start == -1:
          continue

        # TODO: Need to unescape like GetAttr()
        href = s[href_start : href_end]

        new = None
        for prefix, fmt in _REPLACEMENTS:
          if href.startswith(prefix):
            value = href[len(prefix):]
            new = fmt % {'value': value}
            break

        if new is not None:
          out.PrintUntil(href_start)
          f.write(cgi.escape(new))
          out.Skip(href_end)

    elif tok_id == html.EndOfStream:  # Finish it
      out.PrintUntil(start_pos)

    elif tok_id == html.Invalid:
      raise RuntimeError(s[start_pos : end_pos])

    start_pos = end_pos

  return f.getvalue()


def HighlightCode(s):
  f = cStringIO.StringIO()
  out = html.Output(s, f)

  tag_lexer = html.TagLexer()

  for tok_id, end_pos in html.Tokens(s):
    if tok_id == html.StartTag:
      tag_lexer.GetAttr('language')




