#!/usr/bin/env python2
"""
help_gen_test.py: Tests for help_gen.py
"""
from __future__ import print_function

import os
import unittest
from cStringIO import StringIO

from doctools import help_gen  # module under test


class HelpGenTest(unittest.TestCase):

  def testTopicRe(self):
    CASES = [
      ('hello   ', True),
      ('X hello   ', True),
      ('X hello \n', True),
      ('X hello\n', True),
      ('X hello << \n', True),
      ('hello\n', True),
      ('X hello\n', True),
      ]
    for s, matched in CASES:
      m = help_gen.TOPIC_RE.match(s)
      if m:
        print('%r %s' % (s, m.groups()))
        print()

      self.assertEqual(matched, bool(m))

  def testTopicHtml(self):
    os.environ['OILS_VERSION'] = '0.7.pre5'

    # Three spaces before
    #
    # ! for deprecated  -- conflicts with ! bang though
    # X for not implemented

    # Do we need markup here?

    CASES = [
      # leading space required, at least 2 chars
      (2, -1, '   aa bb\n'),
      (3, -1, '   aa bb cc\n'),

      # If end col > linkify_stop_col, then we don't
      # end col is 1-based, like text editors
      (3, 12, '   a1 b4 c7\n'),  # 11 chars not including newline
      (2, 11, '   a1 b4 c7\n'),  # 11 chars not including newline

      (3, -1, '  [Overview] hello   there   X not-impl\n'),

      # Bug fix: 42 was linkified
      (1, -1, '    int-literal   42  65_536  0xFF  0o755  0b10\n'),

      # Bug fix: echo was linkified
      (2, -1, '    expr-splice   echo @[split(x)]  \n'),

      # Bug fix: u was linkified
      (0, -1, "    u'line\\n'  b'byte \yff'\n"),

      # Do we support 2 topics like this?
      (6, -1, '    fork   forkwait        Replace & and (), and takes a block\n'),
      #(2, 20, '    fork   forkwait        Replace & and (), and takes a block\n'),

      (6, -1, '  [Primitive] Bool   Int   Float   Str   Slice   Range\n'),

      # Trailing space
      (4, -1, '  [Process State] X BASHPID   X PPID   UID   EUID  \n'),

      (2, -1, '  [Lexing]        comment #   line-continuation \\\n'),
    ]

    for expected_topics, linkify_stop_col, line in CASES:
      debug_out = []
      r = help_gen.TopicHtmlRenderer('osh', debug_out, linkify_stop_col)

      html = r.Render(line)
      print(html)
      record = debug_out[0]
      print(record)
      actual_topics = len(record['topics'])
      print('%d topics' % actual_topics)

      self.assertEqual(expected_topics, actual_topics,
          'Expected %d topics, got %d: %s' %
          (expected_topics, actual_topics, line))

      print()
      print()

  def testSplitIntoCards(self):
    contents = """
<h2>YSH Expression Language</h2>

expr

<h3>Literals</h2>

oil literals

<h4>oil-numbers</h4>

42 1e100

<h4>oil-array</h4>

%(a b)
"""
    cards = help_gen.SplitIntoCards(['h2', 'h3', 'h4'], contents)
    print(list(cards))


if __name__ == '__main__':
  unittest.main()
