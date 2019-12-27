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


def ExpandLinks(s):
  """
  Expand $xref:bash and so forth
  """
  f = cStringIO.StringIO()
  out = html.Output(s, f)

  tag_lexer = html.TagLexer(s)

  start_pos = 0
  for tok_id, end_pos in html.Tokens(s):
    if tok_id ==  html.StartTag:

      tag_lexer.Reset(start_pos, end_pos)
      if tag_lexer.TagName() == 'a':
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
          out.SkipTo(href_end)

    elif tok_id == html.Invalid:
      raise RuntimeError(s[start_pos : end_pos])

    start_pos = end_pos

  out.PrintTheRest()

  return f.getvalue()


def _ReadUntilClosingTag(s, it, tag_name):
  tag_lexer = html.TagLexer(s)

  start_pos = 0
  while True:
    try:
      tok_id, end_pos = next(it)
    except StopIteration:
      break
    tag_lexer.Reset(start_pos, end_pos)
    if tok_id == html.EndTag and tag_lexer.TagName() == tag_name:
      return start_pos

    start_pos = end_pos

  raise RuntimeError('No closing tag %r' % tag_name)


# Optional newline at end
_LINE_RE = re.compile(r'(.*) \n?', re.VERBOSE)

# flush-left non-whitespace, then dollar and space is considered a prompt
_PROMPT_LINE_RE = re.compile(r'(\S* \$)[ ](.*)', re.VERBOSE)


class PromptLexer(object):
  """
  Highlight shell prompts.
  """

  def __init__(self, s, start_pos, end_pos):
    self.s = s
    self.start_pos = start_pos
    self.end_pos = end_pos

  def PrintHighlighted(self, out):
    pos = self.start_pos
    while pos < self.end_pos:
      m = _LINE_RE.match(self.s, pos, self.end_pos)
      if not m:
        raise RuntimeError("Should have matched a line")
      line_end = m.end(0)

      #log('LINE %r', m.groups())

      m = _PROMPT_LINE_RE.match(self.s, pos, line_end)
      if m:
        #log('MATCH %r', m.groups())

        out.PrintUntil(m.start(1))
        out.Print('<span class="sh-prompt">')
        out.PrintUntil(m.end(1))
        out.Print('</span>')

        out.PrintUntil(m.start(2))
        out.Print('<span class="sh-command">')
        out.PrintUntil(m.end(2))
        out.Print('</span>')

      out.PrintUntil(line_end)

      pos = line_end


def HighlightCode(s):
  """
  Algorithm:
  1. Collect what's inside <pre><code> ...
  2. Then read lines with PromptLexer.
  3. If the line looks like a shell prompt and command, highlight them with
     <span>
  """
  f = cStringIO.StringIO()
  out = html.Output(s, f)

  tag_lexer = html.TagLexer(s)

  start_pos = 0

  it = html.Tokens(s)

  while True:
    try:
      tok_id, end_pos = next(it)
    except StopIteration:
      break

    if tok_id == html.StartTag:

      tag_lexer.Reset(start_pos, end_pos)
      if tag_lexer.TagName() == 'pre':

        start_pos = end_pos
        try:
          tok_id, end_pos = next(it)
        except StopIteration:
          break

        tag_lexer.Reset(start_pos, end_pos)
        if tag_lexer.TagName() == 'code':

          css_class = tag_lexer.GetAttr('class')
          code_start_pos = end_pos
          if css_class is not None and css_class.startswith('language'):
            # Print everything up to and including <pre><code language="...">
            out.PrintUntil(code_start_pos)

            code_end_pos = _ReadUntilClosingTag(s, it, 'code')

            if css_class == 'language-sh-prompt':
              code_lexer = PromptLexer(s, code_start_pos, code_end_pos)
              code_lexer.PrintHighlighted(out)
            else:
              raise RuntimeError('Unknown language %r' % language)

            # We're not writing this
            out.SkipTo(code_end_pos)

    elif tok_id == html.Invalid:
      raise RuntimeError(s[start_pos : end_pos])

    start_pos = end_pos

  out.PrintTheRest()

  return f.getvalue()
