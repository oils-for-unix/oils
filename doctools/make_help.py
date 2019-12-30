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

from doctools import html_lib
from lazylex import html


# Sections have alphabetical characters, spaces, and '/' for I/O.  They are
# turned into anchors.
SECTION_RE = re.compile(r'''
  \s*
  \[
  ([a-zA-Z /:]+)  # colon for oil:nice
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


# Copied from core/comp_ui.py

_RESET = '\033[0;0m'
_BOLD = '\033[1m'
_UNDERLINE = '\033[4m'
_REVERSE = '\033[7m'  # reverse video


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def _StringToHref(s):
  # lower case to match what doctools/cmark.py does
  return s.lower().replace(' ', '-')


# HACK HACK: These happen to have 3 spaces before them! 
_NOT_A_TOPIC = ['compatible', 'egrep']

# BUGS:
# - Continuation lines: hacked with ...
# - Some X before puncutation aren't highlighted

X_LEFT_SPAN = '<span style="color: darkred">'

def HighlightLine(line):
  """Convert a line of text to HTML.

  Topics are highlighted and X made red.

  Args:
    line: RAW SPAN of HTML that is already escaped.

  Returns:
    The HTML with some tags inserted.
  """
  f = cStringIO.StringIO()
  out = html.Output(line, f)

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
    out.Print('<a href="help.html#%s" class="level2">' % href)
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
    out.Print('<a href="help.html#%s">' % topic)
    out.PrintUntil(m.end(2))
    out.Print('</a>')

    # Trailing 3 spaces required to continue.
    if not m.group(4):
      done = True

    pos = m.end(0)

  out.PrintTheRest()

  return f.getvalue()


HTML_REFS = {
    'amp': '&',
    'lt': '<',
    'gt': '>',
    'quot': '"',
}


class Splitter(HTMLParser.HTMLParser):
  """
  Split an HTML stream starting at each of the heading tags.
  
  - h2 for help-index
  - h2, h3, h4 for help

  Content before the first heading is omitted.

  After feed(), self.out is populated with a list of groups, and each group is
  (id_value Str, heading_text Str, parts List[Str]).
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
    log(ind + msg, *args)

  def handle_starttag(self, tag, attrs):
    if tag in self.heading_tags:
      self.in_heading = True
      if self.cur_group:
        self.out.append(self.cur_group)

      values = [v for k, v in attrs if k == 'id']
      id_value = values[0] if len(values) == 1 else None
      self.cur_group = (tag, id_value, [], [])

    self.log('[%d] start tag %s %s', self.indent, tag, attrs)
    self.indent += 1

  def handle_endtag(self, tag):
    if tag in self.heading_tags:
      self.in_heading = False

    self.log('[%d] end tag %s', self.indent, tag)
    self.indent -= 1

  def handle_entityref(self, name):
    """
    From Python docs:
    This method is called to process a named character reference of the form
    &name; (e.g. &gt;), where name is a general entity reference (e.g. 'gt').
    """
    c = HTML_REFS[name]
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
      raise RuntimeError('Unbalanced HTML tags: %d' % self.indent)


def SplitIntoCards(heading_tags, contents):
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

    log('text = %r', text[:10])

    yield tag, topic_id, heading, text

  log('Parsed %d parts', len(groups))


def IndexGroupToText(group_text):
  """
  Note: We cold process some tags, like:

  - Blue Link (not clickable, but still useful)
  - Red X
  """
  f = cStringIO.StringIO()
  out = html.Output(group_text, f)

  pos = 0
  for tok_id, end_pos in html.ValidTokens(group_text):
    if tok_id == html.RawData:
      out.SkipTo(pos)
      out.PrintUntil(end_pos)

    elif tok_id == html.CharEntity:  # &amp;

      entity = group_text[pos+1 : end_pos-1]

      out.SkipTo(pos)
      out.Print(HTML_REFS[entity])
      out.SkipTo(end_pos)

    # Not handling these yet
    elif tok_id == html.HexChar:
      raise AssertionError('Hex Char %r' % group_text[pos : pos + 20])

    elif tok_id == html.DecChar:
      raise AssertionError('Dec Char %r' % group_text[pos : pos + 20])

    pos = end_pos

  out.PrintTheRest()
  return f.getvalue()


def HelpIndexCards(s):
  """
  Given an HTML page, yield groups (id, desc, block of text)
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
        assert css_class == 'language-oil-help-index', tag_lexer.TagString()

        code_end_left, _ = html.ReadUntilEndTag(it, tag_lexer, 'code')

        group_text = s[code_start_right : code_end_left]
        yield group_topic_id, group_name, IndexGroupToText(group_text)

    pos = end_pos


def main(argv):
  action = argv[1]

  if action == 'cards-for-index':
    # Extract sections from help-index.HTML and make them into "cards".

    out_dir = argv[2]
    py_out = argv[3]

    groups = []

    for group_id, group_desc, text in HelpIndexCards(sys.stdin.read()):
      log('group_id = %r', group_id)
      log('group_desc = %r', group_desc)
      #log('text = %r', text)

      # indices start with _
      path = os.path.join(out_dir, '_' + group_id)
      with open(path, 'w') as f:
        f.write('%s %s %s\n\n' % (_REVERSE, group_desc, _RESET))
        f.write(text)
      log('Wrote %s', path)

      groups.append(group_id)

    with open(py_out, 'w') as f:
      f.write('GROUPS = %s\n' % pprint.pformat(groups))
    log('')
    log('Wrote %s', py_out)

  elif action == 'cards':
    # Split help into cards.

    page_path = argv[2]
    index_path = argv[3]  # TODO: Combine with the above
    out_dir = argv[4]
    py_out = argv[5]

    with open(page_path) as f:
      contents = f.read()

    cards = SplitIntoCards(['h2', 'h3', 'h4'], contents)

    topics = []
    for tag, topic_id, heading, text in cards:
      if tag != 'h4':
        continue  # Skip h2 and h3 for now

      log('topic_id = %r', topic_id)
      log('heading = %r', heading)

      # indices start with _
      path = os.path.join(out_dir, topic_id)
      with open(path, 'w') as f:
        f.write('%s %s %s\n\n' % (_REVERSE, heading, _RESET))
        f.write(text)
      log('Wrote %s', path)

      topics.append(topic_id)

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
