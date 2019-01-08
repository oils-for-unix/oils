#!/usr/bin/python -S
"""
pyreadline_test.py: Tests for pyreadline.py
"""
from __future__ import print_function

import unittest

import pyreadline  # module under test


# TODO: Unit tests should test some properties of the output!
# How many lines are there, and did it overflow?

class PyReadlineTest(unittest.TestCase):

  def testPrintPacked(self):
    matches = ['foo', 'bar', 'spam', 'eggs', 'python', 'perl']
    longest_match_len = max(len(m) for m in matches)
    for width in (10, 20, 30, 40, 50):
      n = pyreadline.PrintPacked(matches, longest_match_len, width, 10)
      print('Wrote %d lines' % n)
      print('')

  def testTooMany(self):
    matches = ['--flag%d' % i for i in xrange(100)]
    longest_match_len = max(len(m) for m in matches)
    for width in (10, 20, 30, 40, 50, 60):
      n = pyreadline.PrintPacked(matches, longest_match_len, width, 10)
      print('Wrote %d lines' % n)
      print('')

  def testRootCompleter(self):
    comp_state = {}
    comp_lookup = {
        'echo': pyreadline.WordsAction(['foo', 'bar']),
    }
    display = pyreadline.Display(comp_state, bold_line=True)
    prompt = pyreadline.PromptEvaluator(pyreadline._RIGHT, display)
    reader = pyreadline.InteractiveLineReader('$ ', '> ', prompt, display)
    reader.pending_lines.extend([
        'echo \\\n',  # first line
    ])

    r = pyreadline.RootCompleter(reader, display, comp_lookup, comp_state)
    # second line
    matches = list(r.Matches({'line': 'x f'}))
    print(matches)

    # this is what readline wants
    self.assertEqual(['x foo '], matches)

  def testMakeCompletionRequest(self):
    f = pyreadline.MakeCompletionRequest
    # complete the first word
    self.assertEqual((None, 'ech', '', 0), f(['ech']))

    # complete argument to echo
    self.assertEqual(('echo', '', 'echo ', 5), f(['echo ']))
    self.assertEqual(('echo', 'f', 'echo ', 5), f(['echo f']))

    # CAN complete this
    self.assertEqual(('echo', '', '', 0), f(['echo \\\n', '']))

    # can't complete a first word split over multiple lines without space
    self.assertEqual(-1, f(['ec\\\n', 'ho']))

    # can't complete a first word split over multiple lines with space
    self.assertEqual(-1, f(['ec\\\n', 'ho f']))

    # can't complete last word split over multiple lines
    self.assertEqual(-2, f(['echo f\\\n', 'o']))

    # CAN complete with line break in the middle
    self.assertEqual(('echo', 'b', 'oo ', 3), f(['echo f\\\n', 'oo b']))


if __name__ == '__main__':
  unittest.main()
