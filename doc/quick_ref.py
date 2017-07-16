#!/usr/bin/python
"""
quick_ref.py
"""

import cgi
import re
import sys


CAPS_RE = re.compile(r'^[A-Z ]+$')

# 1. Optional X, then a SINGLE space
# 2. lower-case topic
# 3. Optional: A SINGLE space, then punctuation

TOPIC_RE = re.compile(r'\b(X[ ])?([a-z\-]+)([ ]\S+)?', re.VERBOSE)

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

  print >>sys.stderr, m.groups()

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
    if found_one and prior_piece != '   ':
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


def main(argv):
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


  # TODO: Html Skeleton
  print """\
<!DOCTYPE html>
<html>
  <head>
    <style>
      a:link {
        text-decoration: none;
      }
      a:hover {
        text-decoration: underline;
      }
      body {
        margin: 0 auto;
        width: 50em;
      }
      /* different color because they're links but not topics */
      .level1 {
        /* color: green; */
        color: black;
      }
      .level2 {
        color: #555;
      }
    </style>
  </head>
  <body>
"""
  print '<pre>'

  with open(argv[1]) as f:
    for i, line in enumerate(f):
      if not line.strip():
        sys.stdout.write('\n')
        continue

      if i == 0:
        html_line = '<h1>%s</h1>' % cgi.escape(line)
      elif CAPS_RE.match(line):
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

  print '</pre>'
  print """
  </body>
</html>
"""


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
