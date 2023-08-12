#!/usr/bin/env python
from __future__ import print_function
"""
quick_ref.py
"""

import cgi
import os
import pprint
import re
import sys


# e.g. COMMAND LANGUAGE
CAPS_RE = re.compile(r'^[A-Z ]+$')

# 1. Optional X, then a SINGLE space
# 2. lower-case or upper-case topic
# 3. Optional: A SINGLE space, then punctuation

TOPIC_RE = re.compile(
    r'\b(X[ ])?\@?([a-z_\-]+|[A-Z0-9_]+)([ ]\S+)?', re.VERBOSE)

# Sections have alphabetical characters, spaces, and '/' for I/O.  They are
# turned into anchors.
SECTION_RE = re.compile(r'\s*\[([a-zA-Z /]+)\]')

# Can occur at the beginning of a line, or before a topic
RED_X = '<span style="color: darkred">X </span>'


def _StringToHref(s):
  return s.replace(' ', '-')


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
  section_link = '<a href="#%s" class="level2">%s</a>' % (href, section)
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
    topic_link = '<a href="#%s">%s</a>' % (topic, topic)
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

  # Basically any line that begins with ^# ^### or ^##### is special?
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

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
