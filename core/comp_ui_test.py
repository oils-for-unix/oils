#!/usr/bin/python -S
"""
display_test.py: Tests for display.py
"""
from __future__ import print_function

import cStringIO
import unittest

from core import completion
from core import comp_ui  # module under test


# TODO: Unit tests should test some properties of the output!
# How many lines are there, and did it overflow?

class VisualTest(unittest.TestCase):

  def testPrintPacked(self):
    matches = ['foo', 'bar', 'spam', 'eggs', 'python', 'perl']
    longest_match_len = max(len(m) for m in matches)
    max_lines = 10

    for width in (1, 10, 20, 30, 40, 50):
      f = cStringIO.StringIO()
      n = comp_ui._PrintPacked(matches, longest_match_len, width, max_lines, f)

      out = f.getvalue()
      lines = out.splitlines()
      max_len = max(len(line) for line in lines)

      print('WIDTH = %d' % width)
      print('reported lines = %d' % n)
      print('measured lines = %d' % len(lines))
      print('max_len = %d' % max_len)

      # Make sure it fits in the width!

      # NOTE: This is too conservative because of non-printable characters
      # like \n and ANSI escapes
      if width != 1:
        self.assertLess(max_len, width)

      print('')

  def testLongStringAndSkinnyTerminal(self):
    matches = ['foo' * 10, 'bar' * 10, 'spams' * 10, 'zzz']
    longest_match_len = max(len(m) for m in matches)

    for width in (1, 10, 20, 30, 40, 50):
      f = cStringIO.StringIO()
      n = comp_ui._PrintPacked(matches, longest_match_len, width, 10, f)

      out = f.getvalue()
      lines = out.splitlines()
      max_len = max(len(line) for line in lines)

      print('WIDTH = %d' % width)
      print('reported lines = %d' % n)
      print('measured lines = %d' % len(lines))
      print('max_len = %d' % max_len)
      print('')

  def testTooMany(self):
    matches = ['--flag%d' % i for i in xrange(100)]
    longest_match_len = max(len(m) for m in matches)

    for width in (1, 10, 20, 30, 40, 50, 60):
      f = cStringIO.StringIO()
      n = comp_ui._PrintPacked(matches, longest_match_len, width, 10, f)

      out = f.getvalue()
      lines = out.splitlines()
      max_len = max(len(line) for line in lines)

      print('WIDTH = %d' % width)
      print('reported lines = %d' % n)
      # Count newlines since last one doesn't have a newline
      print('measured lines = %d' % out.count('\n'))
      print('max_len = %d' % max_len)
      print('')

      #print(out)

  def testPrintLong(self):
    matches = ['--all', '--almost-all', '--verbose']
    longest_match_len = max(len(m) for m in matches)
    descriptions = {
        '--all': 'show all ' * 10,  # truncate
        '--almost-all': 'foo',
        '--verbose': 'bar'
    }

    max_lines = 10
    for width in (1, 10, 20, 30, 40, 50, 60):
      f = cStringIO.StringIO()
      n = comp_ui._PrintLong(matches, longest_match_len, width, max_lines,
                        descriptions, f)

      out = f.getvalue()
      lines = out.splitlines()
      max_len = max(len(line) for line in lines)

      print('WIDTH = %d' % width)
      print('reported lines = %d' % n)
      # Count newlines since last one doesn't have a newline
      print('measured lines = %d' % out.count('\n'))
      print('max_len = %d' % max_len)
      print('')

      #print(out)


class UiTest(unittest.TestCase):

  def testNiceDisplay(self):
    comp_state = completion.State()

    disp = comp_ui.NiceDisplay(comp_state, bold_line=False)
    # This one is important
    disp.EraseLines()
    disp.Reset()
    disp.SetPromptLength(10)

    # These are related but we can just set them separately.
    comp_state.orig_line = 'echo '  # for returning to the prompt
    comp_state.suffix_pos = 5  # Strip this off every candidate

    disp.PrintRequired('hello')
    disp.PrintOptional('hello')

    matches = ['echo one', 'echo two']
    disp.PrintCandidates(None, matches, None)

    disp.OnWindowChange()

    # This needs to be aware of the terminal width.
    # It's a bit odd since it's called as a side effect of the PromptEvaluator.
    # That class knows about styles and so forth.

    disp.ShowPromptOnRight('RIGHT')


if __name__ == '__main__':
  unittest.main()
