#!/usr/bin/env python2
"""
oil_doc.py: HTML processing for Oil documentation.
"""
from __future__ import print_function

import cStringIO
import re
import sys

from lazylex import html

_REPLACEMENTS = [
  ('$xref:', '/cross-ref.html?tag=%(value)s#%(value)s'),
  ('$blog-tag:', '/blog/tags.html?tag=%(value)s#%(value)s'),
]


def ExpandLinks(s):
  """
  Expand $xref:bash and so forth
  """
  f = cStringIO.StringIO()
  out = html.Output(s, f)

  for event in html.Parse(s):
    #print(event)
    if isinstance(event, html.StartTag):
      # TODO: Change this to 
      # GetTag(s, p.StartPos())

      if event.Tag() == 'a':
        out.PrintUntil(event.start_pos)

        # eggex:
        # maybe_dq = / '"' ? /
        # pat      = / 'href=' maybe_dq < ~[' >"']* > maybe_dq /

        TAG_RE = re.compile('href= "? ([^ >"]*) "?', re.VERBOSE)
        m = TAG_RE.search(event.s, event.start_pos, event.end_pos)
        if m:
          href = m.group(1)
          new = None
          for prefix, fmt in _REPLACEMENTS:
            if href.startswith(prefix):
              value = href[len(prefix):]
              new = fmt % {'value': value}
              break

          if new is not None:
            out.PrintUntil(m.start(1))
            f.write(new)
            out.Skip(m.end(1))

    elif isinstance(event, html.EndOfStream):  # Finish it
      out.PrintUntil(event.start_pos)

    elif isinstance(event, html.Invalid):
      raise RuntimeError(event)

  return f.getvalue()
