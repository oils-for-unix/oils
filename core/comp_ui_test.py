#!/usr/bin/env python2
"""
display_test.py: Tests for display.py
"""
from __future__ import print_function

import cStringIO
import sys
import unittest

from core import comp_ui  # module under test
from core import util

import line_input


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

  def testDisplays(self):
    comp_ui_state = comp_ui.State()
    prompt_state = comp_ui.PromptState()
    debug_f = util.DebugFile(sys.stdout)

    # terminal width
    d1 = comp_ui.NiceDisplay(80, comp_ui_state, prompt_state, debug_f,
                             line_input, bold_line=False)
    d2 = comp_ui.MinimalDisplay(comp_ui_state, prompt_state, debug_f)

    prompt_state.SetLastPrompt('$ ')

    for disp in [d1, d2]:
      # This one is important
      disp.EraseLines()
      disp.Reset()

      # These are related but we can just set them separately.
      comp_ui_state.line_until_tab = 'echo '  # for returning to the prompt
      comp_ui_state.display_pos = 5  # Strip this off every candidate

      disp.PrintRequired('hello')
      disp.PrintOptional('hello')

      matches = ['echo one', 'echo two']
      disp.PrintCandidates(None, matches, None)

      disp.OnWindowChange()

      # This needs to be aware of the terminal width.
      # It's a bit odd since it's called as a side effect of the PromptEvaluator.
      # That class knows about styles and so forth.

      disp.ShowPromptOnRight('RIGHT')


class PromptTest(unittest.TestCase):

  def testNoEscapes(self):
    for prompt in ["> ", "osh>", "[[]][[]][][]]][["]:
      self.assertEqual(comp_ui._PromptLen(prompt), len(prompt))

  def testValidEscapes(self):
    self.assertEqual(
        comp_ui._PromptLen("\x01\033[01;34m\x02user\x01\033[00m\x02 >"),
        len("user >"))
    self.assertEqual(
        comp_ui._PromptLen("\x01\x02\x01\x02\x01\x02"), 0)
    self.assertEqual(
        comp_ui._PromptLen("\x01\x02 hi \x01hi\x02 \x01\x02 hello"),
        len(" hi   hello"))

  def testNewline(self):
    self.assertEqual(comp_ui._PromptLen("\n"), 0)
    self.assertEqual(comp_ui._PromptLen("abc\ndef"), 3)
    self.assertEqual(comp_ui._PromptLen(""), 0)

  def testControlCharacters(self):
    self.assertEqual(comp_ui._PromptLen("\xef"), 1)
    self.assertEqual(comp_ui._PromptLen("\x03\x05"), 2)


if __name__ == '__main__':
  unittest.main()
