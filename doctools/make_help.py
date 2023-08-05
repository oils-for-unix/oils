#!/usr/bin/env python2
from __future__ import print_function
"""
make_help.py

Ideas for HTML -> ANSI converter:

- `ls`  ->  <code>ls</code>  ->  is reverse video?
- [link]()  ->  <a href="">  ->  underlined, and then add a number to the bottom?
  - could also be bright blue
- <pre> is also indented 4 spaces, like the markdown
- red X <span class="X">X</span>

- comments in code examples could be green?

What about:

- headings h1, h2, h3, h4
  - Right now cards use reverse video.  Centering didn't look great.

- <ul> - you could use a Unicode bullet here
- <ol>

Word wrapping?  troff/groff doesn't do it, but they do this weird right-justify
thing.


- maybe you could have a prefix for a linked word?
  - or use [] ?
  - [SIGTERM]
  - ^SIGTERM
  .SIGTERM
  X .SIGTERM
  X @DIRSTACK
  .for .while .if

Definition lists would be nice:
  $?   exit status
  $0   first etc.
"""

import cStringIO
import HTMLParser
import os
import pprint
import re
import sys

from core import ansi
from doctools import html_lib
from doctools.util import log
from lazylex import html


# Sections have alphabetical characters, spaces, and '/' for I/O.  They are
# turned into anchors.
SECTION_RE = re.compile(r'''
  \s*
  \[
  ([a-zA-Z0-9 /:]+)  # colon for ysh:upgrade
  \]
''', re.VERBOSE)

TOPIC_RE = re.compile(r'''
  (X[ ])?           # optional deprecation symbol X, then a single space
  @?                  # optional @array, e.g. @BASH_SOURCE
  ([a-zA-Z0-9_\-:]+)  # e.g. osh-usage, all:oil, BASH_REMATCH
  ( [ ]\S+            # optional: single space then punctuation
    |
    \(\)              # or func()
  )?      
  ([ ][ ][ ])?        # three spaces means we should keep highlighting
''', re.VERBOSE)


def _StringToHref(s):
  # lower case to match what doctools/cmark.py does
  return s.lower().replace(' ', '-')


# HACK HACK: These happen to have 3 spaces before them! 
_NOT_A_TOPIC = ['compatible', 'egrep']

# BUGS:
# - Continuation lines: hacked with ...
# - Some X before puncutation aren't highlighted

X_LEFT_SPAN = '<span style="color: darkred">'

def HighlightLine(chapter, line):
  """Convert a line of text to HTML.

  Topics are highlighted and X made red.

  Args:
    line: RAW SPAN of HTML that is already escaped.

  Returns:
    The HTML with some tags inserted.
  """
  f = cStringIO.StringIO()
  out = html.Output(line, f)

  if chapter in ('osh', 'ysh'):
    html_page = '%s-help.html' % chapter
  else:
    html_page = 'ref/chap-%s.html' % chapter

  pos = 0 # position within line

  if line.startswith('X '):
    out.Print(X_LEFT_SPAN)
    out.PrintUntil(2)
    out.Print('</span>')
    pos = 2
  elif line.startswith('  '):
    pos = 2
  else:
    return line

  # Highlight [Section] at the start of a line.
  m = SECTION_RE.match(line, pos)
  if m:
    href = _StringToHref(m.group(1))

    out.PrintUntil(m.start(1))
    out.Print('<a href="%s#%s" class="level2">' % (html_page, href))
    out.PrintUntil(m.end(1))  # anchor
    out.Print('</a>')

    pos = m.end(0)  # ADVANCE

  _WHITESPACE = re.compile(r'[ ]+')
  m = _WHITESPACE.match(line, pos)
  assert m, 'Expected whitespace %r' % line

  pos = m.end(0)

  done = False
  while not done:
    # Now just match one
    m = TOPIC_RE.match(line, pos)
    if not m or m.group(2) in _NOT_A_TOPIC:
      break

    if m.group(1):
      out.PrintUntil(m.start(1))
      out.Print(X_LEFT_SPAN)
      out.PrintUntil(m.end(1))
      out.Print('</span>')

    # The linked topic
    topic = m.group(2)

    out.PrintUntil(m.start(2))
    out.Print('<a href="%s#%s">' % (html_page, topic))
    out.PrintUntil(m.end(2))
    out.Print('</a>')

    # Trailing 3 spaces required to continue.
    if not m.group(4):
      done = True

    pos = m.end(0)

  out.PrintTheRest()

  return f.getvalue()


class Splitter(HTMLParser.HTMLParser):
  """Split an HTML stream starting at each of the heading tags.

  For *-help.html.
  
  TODO: Rewrite with this with lazylex!

  Algorithm:
  - ExtractBody() first, then match balanced tags
  - SPLIT by h2, h3, h4
  - Match <pre><code> blocks and re-indent
  - Later:
    - links <a href="">
    - `` is turned into inline <code></code>
    - ** ** for bold
    - * * for emphasis
    - <p> needs word wrapping!  Oops.
      - actually cmark seems to preserve this?  OK maybe not.
      - we just need space between <p>
  """
  def __init__(self, heading_tags, out):
    HTMLParser.HTMLParser.__init__(self)
    self.heading_tags = heading_tags
    self.out = out

    self.cur_group = None  # type: List[Tuple[str, str, List, List]]
    self.in_heading = False

    self.indent = 0

  def log(self, msg, *args):
    ind = self.indent * ' '
    if 0:
      log(ind + msg, *args)

  def handle_starttag(self, tag, attrs):
    if tag in self.heading_tags:
      self.in_heading = True
      if self.cur_group:
        self.out.append(self.cur_group)

      values = [v for k, v in attrs if k == 'id']
      id_value = values[0] if len(values) == 1 else None
      self.cur_group = (tag, id_value, [], [])

    self.log('[%d] <> %s %s', self.indent, tag, attrs)
    self.indent += 1

  def handle_endtag(self, tag):
    if tag in self.heading_tags:
      self.in_heading = False

    self.log('[%d] </> %s', self.indent, tag)
    self.indent -= 1

  def handle_entityref(self, name):
    """
    From Python docs:
    This method is called to process a named character reference of the form
    &name; (e.g. &gt;), where name is a general entity reference (e.g. 'gt').
    """
    c = html.CHAR_ENTITY[name]
    if self.in_heading:
      self.cur_group[2].append(c)
    else:
      if self.cur_group:
        self.cur_group[3].append(c)

  def handle_data(self, data):
    self.log('data %r', data)
    if self.in_heading:
      self.cur_group[2].append(data)
    else:
      if self.cur_group:
        self.cur_group[3].append(data)

  def end(self):
    if self.cur_group:
      self.out.append(self.cur_group)

    # Maybe detect nesting?
    if self.indent != 0:
      raise RuntimeError(
          'Unbalanced HTML tags: indent=%d, cur_group=%s' % (
          self.indent, self.cur_group))


def ExtractBody(s):
  """Extract what's in between <body></body>

  The splitter needs balanced tags, and what's in <head> isn't balanced.
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
      if tag_lexer.TagName() == 'body':
        body_start_right = end_pos  # right after <body>

        out.SkipTo(body_start_right)
        body_end_left, _ = html.ReadUntilEndTag(it, tag_lexer, 'body')

        out.PrintUntil(body_end_left)
        break

    pos = end_pos

  return f.getvalue()


def SplitIntoCards(heading_tags, contents):
  contents = ExtractBody(contents)

  groups = []
  sp = Splitter(heading_tags, groups)
  sp.feed(contents)
  sp.end()

  for tag, id_value, heading_parts, parts in groups:
    heading = ''.join(heading_parts).strip()

    # Don't strip leading space?
    text = ''.join(parts)
    text = text.strip('\n') + '\n'

    topic_id = id_value if id_value else heading.replace(' ', '-')

    #log('text = %r', text[:10])

    yield tag, topic_id, heading, text

  #log('make_help.py: Parsed %d parts', len(groups))


def HelpTopics(s):
  """
  Given an HTML page like {osh,ysh}-help.html,
  Yield groups (id, desc, block of text)
  """
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
      #log('%r', tag_lexer.TagString())
      #log('%r', tag_lexer.TagName())

      # Capture <h2 id="foo"> first
      if tag_lexer.TagName() == 'h2':
        h2_start_right = end_pos

        open_tag_right = end_pos
        group_topic_id = tag_lexer.GetAttr('id')
        assert group_topic_id, 'Expected id= in %r' % tag_lexer.TagString()

        h2_end_left, _ = html.ReadUntilEndTag(it, tag_lexer, 'h2')

        anchor_html = s[h2_start_right : h2_end_left]
        paren_pos = anchor_html.find('(')
        assert paren_pos != -1, anchor_html

        group_name = anchor_html[: paren_pos].strip()

        # Now find the <code></code> span
        _, code_start_right = html.ReadUntilStartTag(it, tag_lexer, 'code')
        css_class = tag_lexer.GetAttr('class') 
        assert css_class.startswith('language-chapter-links-'), tag_lexer.TagString()

        code_end_left, _ = html.ReadUntilEndTag(it, tag_lexer, 'code')

        text = html.ToText(s, code_start_right, code_end_left)
        yield group_topic_id, group_name, text

    pos = end_pos


def main(argv):
  action = argv[1]

  if action == 'cards-from-index':
    sh = argv[2]  # osh or ysh
    out_prefix = argv[3]

    f = sys.stdout
    groups = []
    for group_id, group_desc, text in HelpTopics(sys.stdin.read()):
      #log('group_id = %r', group_id)
      #log('group_desc = %r', group_desc)
      #log('text = %r', text)

      topic = '%s-%s' % (sh, group_id)  # e.g. ysh-overview

      path = os.path.join(out_prefix, topic)
      with open(path, 'w') as f:
        f.write('%s %s %s\n\n' % (ansi.REVERSE, group_desc, ansi.RESET))
        f.write(text)
        f.write('\n')  # extra
      log('  Wrote %s', path)
      groups.append(group_id)

    log('  (doctools/make_help) -> %d groups', len(groups))

  elif action == 'cards-from-chapter':

    out_dir = argv[2]
    py_out = argv[3]
    tag_level = argv[4]  # h4 or h3
    pages = argv[5:]

    topics = []
    seen = set()
    for page_path in pages:
      with open(page_path) as f:
        contents = f.read()

      cards = SplitIntoCards(['h2', 'h3', 'h4'], contents)

      for tag, topic_id, heading, text in cards:
        if tag != tag_level:
          continue  # Skip h2 and h3 for now

        #log('topic_id = %r', topic_id)
        #log('heading = %r', heading)

        # indices start with _
        path = os.path.join(out_dir, topic_id)
        with open(path, 'w') as f:
          f.write('%s %s %s\n\n' % (ansi.REVERSE, heading, ansi.RESET))
          f.write(text)

        topics.append(topic_id)
        if topic_id in seen:
          log('Warning: %r is duplicated', topic_id)
        seen.add(topic_id)

    log('%s -> (doctools/make_help) -> %d cards in %s', ' '.join(pages), len(topics), out_dir)

    with open(py_out, 'w') as f:
      f.write('TOPICS = %s\n' % pprint.pformat(topics))

    # Process pages first, so you can parse 
    # <h4 class="discouarged oil-language osh-only bash ksh posix"></h4>
    #
    # And then the cards can be highlighted?  Or at least have the markup to be
    # able to do so.
    #
    # help index intro
    # help -color=0 index intro  # no color
    #
    # Highlight tags with two different colors
    # help -tag=oil-language -tag bash index intro  # no color

    # Make text for the app bundle.  HTML is made by build/doc.sh

    # names are <h4 id="if" keywords="elif fi">...</h2>

    # NOTE: This has to go through MARKDOWN to parse:
    # `code` and indented

    # TODO:
    # - read help.md
    # - split <h4></h4>
    #   - how?  From beginning of <h4> until next <h> tag?
    # - assign it an ID for TOPIC_LOOKUP
    #   - either the prettified name, or or an explicit id=""
    #   - like doctools/cmark.py
    # - then parse the HTML
    #   - turn <code></code> into INVERTED
    #   - turn <a> into UNDERLINE
    #     - and then add at the bottom
    #   - process
    #     - $quick-ref:for
    #     - $cross-ref:bash

    # then output TOPIC_LOOKUP

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)


# vim: sw=2
