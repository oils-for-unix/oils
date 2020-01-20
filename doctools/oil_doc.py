#!/usr/bin/env python2
"""
oil_doc.py: HTML processing for Oil documentation.

Plugins:
  ExpandLinks expands $xref, etc.
  PygmentsPlugin -- for ```python, ```sh, ```c, etc.
  HelpIndexPlugin -- for help-index.html

  ShPromptPlugin -- understands $ echo hi, but doesn't run anything
  ShSession -- runs shell snippets and caches the output
"""
from __future__ import print_function

import cgi
import cStringIO
import re
import sys

from lazylex import html

log = html.log


def RemoveComments(s):
  """ Remove <!-- comments --> """
  f = cStringIO.StringIO()
  out = html.Output(s, f)

  tag_lexer = html.TagLexer(s)

  pos = 0

  for tok_id, end_pos in html.ValidTokens(s):
    if tok_id == html.Comment:
      value = s[pos : end_pos]
      # doc/release-index.md has <!-- REPLACE_WITH_DATE --> etc.
      if 'REPLACE' not in value:
        out.PrintUntil(pos)
        out.SkipTo(end_pos)
    pos = end_pos

  out.PrintTheRest()
  return f.getvalue()


class _Abbrev(object):
  def __init__(self, fmt):
    self.fmt = fmt

  def __call__(self, value):
    return self.fmt % {'value': value}


_ABBREVIATIONS = {
  'xref':
      _Abbrev('/cross-ref.html?tag=%(value)s#%(value)s'),
  'blog-tag':
      _Abbrev('/blog/tags.html?tag=%(value)s#%(value)s'),
  'oil-commit':
      _Abbrev('https://github.com/oilshell/oil/commit/%(value)s'),
  'oil-src':
      _Abbrev('https://github.com/oilshell/oil/blob/master/%(value)s'),
  'blog-code-src':
      _Abbrev('https://github.com/oilshell/blog-code/blob/master/%(value)s'),
  'issue':
      _Abbrev('https://github.com/oilshell/oil/issues/%(value)s'),
}

# $xref:foo
_SHORTCUT_RE = re.compile(r'\$ ([a-z\-]+) (?: : (\S+))?', re.VERBOSE)


def ExpandLinks(s):
  """
  Expand $xref:bash and so forth
  """
  f = cStringIO.StringIO()
  out = html.Output(s, f)

  tag_lexer = html.TagLexer(s)

  pos = 0

  it = html.ValidTokens(s)
  while True:
    try:
      tok_id, end_pos = next(it)
    except StopIteration:
      break

    if tok_id ==  html.StartTag:

      tag_lexer.Reset(pos, end_pos)
      if tag_lexer.TagName() == 'a':
        open_tag_right = end_pos

        href_start, href_end = tag_lexer.GetSpanForAttrValue('href')
        if href_start == -1:
          continue

        # TODO: Need to unescape like GetAttr()
        href = s[href_start : href_end]

        new = None
        m = _SHORTCUT_RE.match(href)
        if m:
          abbrev_name, arg = m.groups()
          if not arg:
            close_tag_left, _ = html.ReadUntilEndTag(it, tag_lexer, 'a')
            arg = s[open_tag_right : close_tag_left]

          func = _ABBREVIATIONS.get(abbrev_name)
          if not func:
            raise RuntimeError('Invalid abbreviation %r' % abbrev_name)
          new = func(arg)

        if new is not None:
          out.PrintUntil(href_start)
          f.write(cgi.escape(new))
          out.SkipTo(href_end)

    pos = end_pos

  out.PrintTheRest()

  return f.getvalue()


class _Plugin(object):

  def __init__(self, s, start_pos, end_pos):
    self.s = s
    self.start_pos = start_pos
    self.end_pos = end_pos

  def PrintHighlighted(self, out):
    raise NotImplementedError()


# Optional newline at end
_LINE_RE = re.compile(r'(.*) \n?', re.VERBOSE)

_PROMPT_LINE_RE = re.compile(r'''
(\S* \$)[ ]       # flush-left non-whitespace, then dollar and space is a prompt
(.*?)             # arbitrary text
(?:               # don't highlight tab completion
  (&lt;TAB&gt;)   # it's HTML escaped!!!
  .*?
)?
(?:
  [ ][ ]([#] .*)  # optionally: two spaces then a comment
)?
$
''', re.VERBOSE)


_COMMENT_RE = re.compile(r'''
.*?             # arbitrary text
[ ][ ]([#] .*)  # two spaces then a comment
$
''', re.VERBOSE)


def Lines(s, start_pos, end_pos):
  pos = start_pos
  while pos < end_pos:
    m = _LINE_RE.match(s, pos, end_pos)
    if not m:
      raise RuntimeError("Should have matched a line")
    line_end = m.end(0)

    yield line_end

    pos = line_end


class ShPromptPlugin(_Plugin):
  """
  Highlight shell prompts.
  """

  def PrintHighlighted(self, out):
    pos = self.start_pos
    for line_end in Lines(self.s, self.start_pos, self.end_pos):

      # TODO:  Check for comments on non-prompt lines too?

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

        if m.group(3):
          out.PrintUntil(m.start(3))
          out.Print('<span class="sh-tab-complete">')
          out.PrintUntil(m.end(3))
          out.Print('</span>')

        if m.group(4):
          out.PrintUntil(m.start(4))
          out.Print('<span class="sh-comment">')
          out.PrintUntil(m.end(4))
          out.Print('</span>')
      else:
        m = _COMMENT_RE.match(self.s, pos, line_end)
        if m:
          out.PrintUntil(m.start(1))
          out.Print('<span class="sh-comment">')
          out.PrintUntil(m.end(1))
          out.Print('</span>')

      out.PrintUntil(line_end)

      pos = line_end


class HelpIndexPlugin(_Plugin):
  """
  Highlight blocks of help-index.md.
  """
  def PrintHighlighted(self, out):
    from doctools import make_help

    pos = self.start_pos
    for line_end in Lines(self.s, self.start_pos, self.end_pos):
      # NOTE: HighlightLine accepts an HTML ESCAPED line.  It's valid to just
      # add tags and leave everything alone.
      line = self.s[pos : line_end]

      html_line = make_help.HighlightLine(line)

      if html_line is not None:
        out.PrintUntil(pos)
        out.Print(html_line)
        out.SkipTo(line_end)

      pos = line_end


class PygmentsPlugin(_Plugin):

  def __init__(self, s, start_pos, end_pos, lang):
    _Plugin.__init__(self, s, start_pos, end_pos)
    self.lang = lang

  def PrintHighlighted(self, out):
    from pygments import lexers
    from pygments import formatters
    from pygments import highlight

    lexer = lexers.get_lexer_by_name(self.lang)

    formatter = formatters.HtmlFormatter()
    code = self.s[self.start_pos : self.end_pos]
    highlighted = highlight(code, lexer, formatter)
    out.Print(highlighted)


def HighlightCode(s):
  """
  Algorithm:
  1. Collect what's inside <pre><code> ...
  2. Then read lines with ShPromptPlugin.
  3. If the line looks like a shell prompt and command, highlight them with
     <span>
  """
  f = cStringIO.StringIO()
  out = html.Output(s, f)

  tag_lexer = html.TagLexer(s)

  pos = 0

  it = html.ValidTokens(s)

  while True:
    try:
      tok_id, end_pos = next(it)
    except StopIteration:
      break

    if tok_id == html.StartTag:

      tag_lexer.Reset(pos, end_pos)
      if tag_lexer.TagName() == 'pre':
        pre_start_pos = pos
        pos = end_pos

        try:
          tok_id, end_pos = next(it)
        except StopIteration:
          break

        tag_lexer.Reset(pos, end_pos)
        if tok_id == html.StartTag and tag_lexer.TagName() == 'code':

          css_class = tag_lexer.GetAttr('class')
          code_start_pos = end_pos
          if css_class is not None and css_class.startswith('language'):

            slash_code_left, slash_code_right = \
                html.ReadUntilEndTag(it, tag_lexer, 'code')

            if css_class == 'language-sh-prompt':
              # Here's we're KEEPING the original <pre><code>
              # Print everything up to and including <pre><code language="...">
              out.PrintUntil(code_start_pos)

              plugin = ShPromptPlugin(s, code_start_pos, slash_code_left)
              plugin.PrintHighlighted(out)

              out.SkipTo(slash_code_left)

            elif css_class == 'language-oil':
              # TODO: Write an Oil syntax highlighter.
              pass

            elif css_class == 'language-oil-help-index':

              out.PrintUntil(code_start_pos)

              plugin = HelpIndexPlugin(s, code_start_pos, slash_code_left)
              plugin.PrintHighlighted(out)

              out.SkipTo(slash_code_left)

            else:
              # Here's we're REMOVING the original <pre><code>
              # Pygments gives you a <pre> already

              # We just read closing </code>, and the next one should be </pre>.
              try:
                tok_id, end_pos = next(it)
              except StopIteration:
                break
              tag_lexer.Reset(slash_code_right, end_pos)
              assert tok_id == html.EndTag, tok_id
              assert tag_lexer.TagName() == 'pre', tag_lexer.TagName()
              slash_pre_right = end_pos

              out.PrintUntil(pre_start_pos)

              lang = css_class[len('language-'):]
              plugin = PygmentsPlugin(s, code_start_pos, slash_code_left, lang)
              plugin.PrintHighlighted(out)

              out.SkipTo(slash_pre_right)
              f.write('<!-- done pygments -->\n')

    pos = end_pos

  out.PrintTheRest()

  return f.getvalue()


class ShellSession(object):
  """
  TODO: Pass this to HighlightCode as a plugin

  $ x=one
  $ echo $x
  $ echo two

  Becomes

  $ x=one
  $ echo $x
  one
  $ echo two
  two

  And then you will have
  blog/2019/12/_shell_session/
    $hash1-stdout.txt
    $hash2-stdout.txt

  It hashes the command with md5 and then brings it back.
  If the file already exists then it doesn't run it again.
  You can delete the file to redo it.

  TODO: write a loop that reads one line at a time, writes, it, then reads
  output from bash.
  Use the Lines iterator to get lines.
  For extra credit, you can solve the PS2 problem?  That's easily done with
  Oil's parser.
  """
  def __init__(self, shell_exe, cache_dir):
    """
    Args:
      shell_exe: sh, bash, osh, or oil.  Use the one in the $PATH by default.
      cache_dir: ~/git/oilshell/oilshell.org/blog/2019/12/session/
    """
    self.shell_exe = shell_exe
    self.cache_dir = cache_dir

  def PrintHighlighted(self, s, start_pos, end_pos, out):
    """
    Args:
      s: an HTML string.
    """
    pass
