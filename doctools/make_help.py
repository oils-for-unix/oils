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

TODO:
  handle_startendtag()
  handle_decl() -- for doctype

https://bugs.python.org/issue25258
"""

import cgi
import HTMLParser
import os
import pprint
import re
import sys

import html_lib

# e.g. COMMAND LANGUAGE
CAPS_RE = re.compile(r'^[A-Z ]+$')

# Sections have alphabetical characters, spaces, and '/' for I/O.  They are
# turned into anchors.
SECTION_RE = re.compile(r'''
\s*
\[
([a-zA-Z /]+)
\]
''', re.VERBOSE)

TOPIC_RE = re.compile(r'''
\b(X[ ])?           # optional deprecation symbol X, then a single space
@?                  # optional @array, e.g. @BASH_SOURCE
([a-zA-Z0-9_\-:]+)  # e.g. osh-usage, all:oil, BASH_REMATCH
( [ ]\S+            # optional: single space then punctuation
  |
  \(\)              # or func()
)?      
''', re.VERBOSE)


# Can occur at the beginning of a line, or before a topic
RED_X = '<span style="color: darkred">X </span>'


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


def MaybeHighlightSection(line, parts):
  """
  Highlight [Section] at the start of a line.
  """
  m = SECTION_RE.match(line)
  if not m:
    return line

  #print >>sys.stderr, m.groups()

  start = m.start(1)
  end = m.end(1)
  parts.append(line[:start])  # this is spaces, so not bothering to escape

  section = m.group(1)
  href = _StringToHref(section)
  section_link = '<a href="help.html#%s" class="level2">%s</a>' % (href, section)
  parts.append(section_link)

  return line[end:]


def HighlightLine(line):
  """Convert a line of text to HTML.

  Topics are highlighted and X made red.

  Args:
    line: RAW SPAN of HTML that is already escaped.

  Returns:
    The HTML with some tags inserted.
  """
  parts = []
  last_end = 0
  found_one = False

  line = MaybeHighlightSection(line, parts)

  for m in TOPIC_RE.finditer(line):
    #print >>sys.stderr, m.groups()

    have_x = m.group(1) is not None
    start = m.start(1) if have_x else m.start(2)

    have_suffix = m.group(3) is not None

    prior_piece = line[last_end:start]
    parts.append(prior_piece)

    if have_x:
      parts.append(RED_X)

    # Topics on the same line must be separated by exactly THREE spaces
    if found_one and prior_piece not in ('   ', '   @'):
      last_end = start
      break  # stop linking

    # this matters because the separator is three spaces
    end = m.end(3) if have_suffix else m.end(2)
    last_end = end

    topic = line[m.start(2):m.end(2)]
    topic_link = '<a href="help.html#%s">%s</a>' % (topic, topic)
    parts.append(topic_link)

    if have_suffix:
      parts.append(m.group(3))

    found_one = True

  last_piece = line[last_end:len(line)]
  parts.append(last_piece)

  #print >>sys.stderr, parts

  html_line = ''.join(parts)
  #print >>sys.stderr, html_line

  return html_line


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


def main(argv):
  action = argv[1]

  if action == 'text-index':
    # Make text for the app bundle.  HTML is made by build/doc.sh

    # 1. Read help-index.md
    #    split <h2></h2>
    # 2. Output a text file for each group, which appears in a <div>
    #
    # The whole file is also processed by doctools/cmark.py.
    # Or we might want to make a special HTML file?

    # names are <h2 id="intro">...</h2>

    # TODO: title needs to be centered in text?

    out_dir = argv[2]
    py_out = argv[3]

    groups = []
    for tag, topic_id, heading, text in SplitIntoCards(['h2'], sys.stdin.read()):
      log('topic_id = %r', topic_id)
      log('heading = %r', heading)
      #log('text = %r', text)

      # indices start with _
      path = os.path.join(out_dir, '_' + topic_id)
      with open(path, 'w') as f:
        f.write('%s %s %s\n\n' % (_REVERSE, heading, _RESET))
        f.write(text)
      log('Wrote %s', path)

      groups.append(topic_id)

    with open(py_out, 'w') as f:
      f.write('GROUPS = %s\n' % pprint.pformat(groups))

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
