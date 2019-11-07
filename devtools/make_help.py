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

import cgi
import HTMLParser
import os
import pprint
import re
import sys

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
  # lower case to match what devtools/cmark.py does
  return s.lower().replace(' ', '-')


def MaybeHighlightSection(line, parts):
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

  Topics are highlighted and X made red."""

  parts = []
  last_end = 0
  found_one = False

  line = MaybeHighlightSection(line, parts)

  for m in TOPIC_RE.finditer(line):
    #print >>sys.stderr, m.groups()

    have_x = m.group(1) is not None
    start = m.start(1) if have_x else m.start(2)

    have_suffix = m.group(3) is not None

    prior_piece = cgi.escape(line[last_end:start])
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
      parts.append(cgi.escape(m.group(3)))

    found_one = True

  last_piece = cgi.escape(line[last_end:len(line)])
  parts.append(last_piece)

  #print >>sys.stderr, parts

  html_line = ''.join(parts)
  #print >>sys.stderr, html_line

  return html_line


def TableOfContents(f):


  # inputs: -toc.txt, -pages.txt

  # outputs:
  #   tree of HTML

  # maybe: man page for OSH usage (need to learn troff formatting!)

  # syntactic elements:
  # - toc
  #   - links to pages
  #   - (X) for not implemented
  #   - aliases:  semicolon ;
  # - pages
  #   - usage line (^Usage:)
  #   - internal links read[1]
  #     - <a href="#read"><read>
  #     - read[1]
  #
  #   - example blocks

  # generated parts:
  #  - builtin usage lines, from core/args.py
  #  - and osh usage itself

  # Language:

  ##### COMMAND LANGUAGE  (turns into <a name=>)
  ### Commands
  # case
  # if

  # Basically any line that begins with ^# ^### or ^##### is speical?
  # <h1> <h2> <h3>
  # Still need links

  # TODO:
  # - Copy sh_spec.py for # parsing
  # - Copy oilshell.org Snip for running examples and showing output!

  # More stuff:
  # - command, word, arith, boolean all need intros.
  # - So does every section need a name?
  # - Maybe just highlight anything after [?
  #   - What kind of links are they?

  # Three level hierarchy:
  # CAP WORDS
  # [Title Words For Sections]
  #  problem: line brekas like [Shell Process
  #    Control]
  #  there is no valid way to mark this up, even if you could parse it!
  #    you would need a table?

  # lower-with-dashes for topics


  # TODO: Add version and so forht?
  title_line = f.readline()
  print('<h1>%s</h1>' % cgi.escape(title_line))
  print('<a name="toc"></a>')
  # doc/run.sh must set environment.
  print('<i>Version %s</i>' % os.environ['OIL_VERSION'])
  print('<pre>')

  for line in f:
    if not line.strip():
      sys.stdout.write('\n')
      continue

    if CAPS_RE.match(line):
      heading = line.strip()
      anchor_text = cgi.escape(heading)
      href = _StringToHref(heading)
      # Add the newline back here
      html_line = '<b><a href="#%s" class="level1">%s</a></b>\n' % (
          href, anchor_text)
    elif line.startswith('  '):
      html_line = HighlightLine(line)
    elif line.startswith('X '):
      html_line = RED_X + HighlightLine(line[2:])
    else:
      html_line = cgi.escape(line)

    sys.stdout.write(html_line)

  print('</pre>')

# TODO:
# - group 1: # prefix determines h1, h2, h3
# - group 2 is the <a name=""> -- there can be MORE THAN ONE
#   - OSH-BINARY
#   - Commands
#   - for-expr
#   - true|false
# - group 3: the anchor text to display
#

## Conditional Conditional Constructs
## Quotes Quotes
### COMMAND-LANGUAGE Command Language

### {Conditional} Conditional Constructs
### <Conditional> Conditional Constructs

# These have no title?  Just true?  false?

# true|false true


class TextOutput:
  def __init__(self, text_dir, topic_lookup):
    self.text_dir = text_dir
    self.topic_lookup = topic_lookup

  def WriteFile(self, section_id, topics, lines):
    """
    """
    section_name = '%d-%d-%d' % tuple(section_id)
    path = os.path.join(self.text_dir, section_name)
    with open(path, 'w') as f:
      for line in lines:
        f.write(line)
    #print >>sys.stderr, 'Wrote %s' % path

    for topic in topics:
      self.topic_lookup[topic] = section_name


# TODO: Also allow {} in addition to <> delimiters.
HEADING_RE = re.compile(r'(#+) <(.*)>(.*)')

def Pages(f, text_out):
  print('<pre>')

  section_id = [0, 0, 0]  # L1, L2, L3
  topics = []
  prev_topics = []  # from previous iteration
  prev_lines = []

  for line in f:
    if line.startswith('##'):  # heading or comment
      m = HEADING_RE.match(line)
      if m:
        # We got a heading.  Write the previous lines
        text_out.WriteFile(section_id, prev_topics, prev_lines)
        prev_lines = []

        level, topic_str, text = m.groups()
        #print >>sys.stderr, m.groups()
        topics = topic_str.split()
        if not text.strip():
          text = topic_str

        if len(level) == 5:
          htag = 2
          section_id[0] += 1  # from 2.3.4 to 3.0.0
          section_id[1] = 0
          section_id[2] = 0

        elif len(level) == 4:
          htag = 3
          section_id[1] += 1  # from 2.2.3 to 2.3.0
          section_id[2] = 0

        elif len(level) == 3:
          htag = 4
          section_id[2] += 1  # from 2.2.2 to 2.2.3

        else:
          raise RuntimeError('Invalid level %r' % level)

        print('</pre>')
        for topic in topics:
          print('<a name="%s"></a>' % topic)
        print('<h%d>%s</h%d>' % (htag, text, htag))
        print('<!-- %d.%d.%d -->' % tuple(section_id))
        print('<pre>')

        prev_topics = topics

      else:
        # Three or more should be a heading, not a comment.
        if line.startswith('###'):
          raise RuntimeError('Expected a heading, got %r' % line)

    else:  # normal line
      sys.stdout.write(cgi.escape(line))
      prev_lines.append(line)
      continue

  print('</pre>')


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

  TODO: Share HTML tag reconstruction with IndexLinker
  """
  def __init__(self, heading_tags, out):
    HTMLParser.HTMLParser.__init__(self)
    self.heading_tags = heading_tags
    self.out = out

    self.cur_group = None  # type: List[Tuple[str, List, List]]
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
      self.cur_group = (id_value, [], [])

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
      self.cur_group[1].append(c)
    else:
      if self.cur_group:
        self.cur_group[2].append(c)

  def handle_data(self, data):
    self.log('data %r', data)
    if self.in_heading:
      self.cur_group[1].append(data)
    else:
      if self.cur_group:
        self.cur_group[2].append(data)

  def end(self):
    if self.cur_group:
      self.out.append(self.cur_group)

    # Maybe detect nesting?
    if self.indent != 0:
      raise RuntimeError('Unbalanced HTML tags: %d' % self.indent)


def _LinkLine(line):
  if line.startswith('  '):
    html_line = HighlightLine(line)
  elif line.startswith('X '):
    html_line = RED_X + HighlightLine(line[2:])
  else:
    html_line = cgi.escape(line)
  return html_line


class IndexLinker(HTMLParser.HTMLParser):

  def __init__(self, pre_class, out):
    HTMLParser.HTMLParser.__init__(self)
    self.indent = 0  # checking

    self.pre_parts = []  # stuff to highlight

    self.out = out

    self.linking = False

  def log(self, msg, *args):
    return
    ind = self.indent * ' '
    log(ind + msg, *args)

  def handle_starttag(self, tag, attrs):
    if tag == 'pre':
      values = [v for k, v in attrs if k == 'class']
      class_name = values[0] if len(values) == 1 else None

      if class_name:
        self.linking = True

    # TODO: Change href="$help:command" to href="help.html#command"
    if attrs:
      attr_str = ' '  # leading space
      attr_str += ' '.join('%s="%s"' % (k, v) for (k, v) in attrs)
    else:
      attr_str = ''
    self.out.write('<%s%s>' % (tag, attr_str))

    self.log('start tag %s %s', tag, attrs)
    self.indent += 1

  def handle_endtag(self, tag):
    if tag == 'pre':
      self.linking = False

      lines = ''.join(self.pre_parts).splitlines()
      for line in lines:
        #self.out.write('|')
        self.out.write(_LinkLine(line))
        self.out.write('\n')

      self.pre_parts = []

    self.out.write('</%s>' % tag)

    self.log('end tag %s', tag)
    self.indent -= 1

  def handle_entityref(self, name):
    """
    From Python docs:
    This method is called to process a named character reference of the form
    &name; (e.g. &gt;), where name is a general entity reference (e.g. 'gt').
    """
    c = HTML_REFS[name]
    if self.linking:
      self.pre_parts.append(c)
    else:
      self.out.write(c)

  def handle_data(self, data):
    if self.linking:
      self.pre_parts.append(data)
    else:
      self.out.write(data)

  def end(self):
    return
    # Maybe detect nesting?
    if self.indent != 0:
      raise RuntimeError('Unbalanced HTML tags: %d' % self.indent)


def SplitIntoCards(heading_tags, contents):
  groups = []
  sp = Splitter(heading_tags, groups)
  sp.feed(contents)
  sp.end()

  for id_value, heading_parts, parts in groups:
    heading = ''.join(heading_parts).strip()

    # Don't strip leading space?
    text = ''.join(parts)
    text = text.strip('\n') + '\n'

    topic_id = id_value if id_value else heading.replace(' ', '-')

    log('text = %r', text[:10])

    yield topic_id, heading, text

  log('Parsed %d parts', len(groups))


def main(argv):
  action = argv[1]
  if action == 'toc':
    with open(argv[2]) as f:
      TableOfContents(f)

  elif action == 'pages':
    pages_txt, text_dir, py_out_path = argv[2:5]

    topic_lookup = {}
    with open(pages_txt) as f:
      text_out = TextOutput(text_dir, topic_lookup)
      Pages(f, text_out)

    # TODO: Fuzzy matching of help topics
    d = pprint.pformat(topic_lookup)
    #print >>sys.stderr, d
    with open(py_out_path, 'w') as f:
      f.write('TOPIC_LOOKUP = ')
      f.write(d)
      # BUG WORKAROUND: The OPy parser requires an EOL!  See opy/run.sh parser-bug.
      f.write('\n')

    print('Wrote %s/ and %s' % (text_dir, py_out_path), file=sys.stderr)

  elif action == 'text-index':
    # Make text for the app bundle.  HTML is made by build/doc.sh

    # 1. Read help-index.md
    #    split <h2></h2>
    # 2. Output a text file for each group, which appears in a <div>
    #
    # The whole file is also processed by devtools/cmark.py.
    # Or we might want to make a special HTML file?

    # names are <h2 id="intro">...</h2>

    # TODO: title needs to be centered in text?

    out_dir = argv[2]
    for topic_id, heading, text in SplitIntoCards(['h2'], sys.stdin.read()):
      log('topic_id = %r', topic_id)
      log('heading = %r', heading)
      #log('text = %r', text)

      # indices start with _
      path = os.path.join(out_dir, '_' + topic_id)
      with open(path, 'w') as f:
        f.write('%s %s %s\n\n' % (_REVERSE, heading, _RESET))
        f.write(text)
      log('Wrote %s', path)

  elif action == 'html-index':
    # TODO: We could process the pages first like in 'cards', and
    # change the index rendering.

    # TODO: parse all the <pre class="help-index"> blocks
    sp = IndexLinker('help-index', sys.stdout)
    sp.feed(sys.stdin.read())
    sp.end()

    # Maybe combine Splitter and IndexLinker?
    # IndexParser?
    # But the probably is it's not lossless!!!  We want to replace
    # - <pre></pre>
    # - maybe <h2> with a link to "help.html#cmd"

  elif action == 'cards':
    page_path = argv[2]
    index_path = argv[3]
    out_dir = argv[4]

    with open(page_path) as f:
      contents = f.read()

    #cards = SplitIntoCards(['h2', 'h3', 'h4'], contents)

    # Only do h4 for now
    cards = SplitIntoCards(['h4'], contents)

    for topic_id, heading, text in cards:
      log('topic_id = %r', topic_id)
      log('heading = %r', heading)

      # indices start with _
      path = os.path.join(out_dir, topic_id)
      with open(path, 'w') as f:
        f.write('* %s\n\n' % heading)
        f.write(text)
      log('Wrote %s', path)

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
    #   - like devtools/cmark.py
    # - then parse the HTML
    #   - turn <code></code> into INVERTED
    #   - turn <a> into UNDERLINE
    #     - and then add at the bottom
    #   - process
    #     - $quick-ref:for
    #     - $cross-ref:bash

    # then output TOPIC_LOOKUP

    pass

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
