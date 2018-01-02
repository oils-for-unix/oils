#!/usr/bin/python -S
"""
legacy_test.py: Tests for legacy.py
"""

import unittest

from core import legacy  # module under test


def _RunSplitCases(test, sp, cases):

  for expected_parts, s, allow_escape in cases:
    spans = sp.Split(s, allow_escape)
    print('%r: %s' % (s, spans))

    parts = []
    start_index = 0
    for ignored, end_index in spans:
      if not ignored:
        parts.append(s[start_index:end_index])
      start_index = end_index

    test.assertEqual(expected_parts, parts,
        '%r: %s != %s' % (s, expected_parts, parts))


class SplitTest(unittest.TestCase):

  def testDefaultIfs(self):
    CASES = [
        ([], '', True),
        (['a'], 'a', True),
        (['a'], ' a ', True),
        (['ab'], '\tab\n', True),
        (['a', 'b'], 'a  b\n', True),
    ]

    sp = legacy.WhitespaceSplitter(legacy.DEFAULT_IFS)
    _RunSplitCases(self, sp, CASES)

  def testMixedIfs(self):
    CASES = [
        ([], '', True),
        (['a', 'b'], 'a_b', True),
        (['a', 'b'], ' a b ', True),
        (['a', 'b'], 'a _ b', True),
        (['a', 'b'], '  a _ b  ', True),
        (['a', '', 'b'], 'a _ _ b', True),
        (['a', '', 'b'], 'a __ b', True),
        (['a', '', '', 'b'], 'a _  _ _  b', True),

        (['a'], '  a _ ', True),

        # Contrast with the case above.

        # NOTES:
        # - This cases REQUIRES ignoring leading whitespace.  The state machine
        # can't handle it.
        # - We get three spans with index 1 because of the initial rule to
        # ignore whitespace, and then EMIT_EMPTY.  Seems harmless for now?
        (['', 'a'], ' _ a _ ', True),
    ]

    # IFS='_ '
    sp = legacy.MixedSplitter(' ', '_')
    _RunSplitCases(self, sp, CASES)

  def testWhitespaceOnly(self):
    CASES = [
        ([], '', True),
        ([], '\t', True),
        (['a'], 'a\t', True),
        (['a', 'b'], '\t\ta\tb\t', True),
    ]

    # IFS='_ '
    sp = legacy.MixedSplitter('\t', '')
    _RunSplitCases(self, sp, CASES)

  def testOtherOnly(self):
    CASES = [
        ([], '', True),
        ([''], '_', True),
        (['a'], 'a_', True),
        (['', '', 'a', 'b'], '__a_b_', True),
    ]

    # IFS='_ '
    sp = legacy.MixedSplitter('', '_')
    _RunSplitCases(self, sp, CASES)

  def testTwoOther(self):
    CASES = [
        (['a', '', 'b', '', '', 'c', 'd'], 'a__b---c_d', True)
    ]

    # IFS='_ '
    sp = legacy.MixedSplitter('', '_-')
    _RunSplitCases(self, sp, CASES)


class OldSplitTest(unittest.TestCase):

  def testIfsSplitEmpty(self):
    self.assertEqual(
        [''], legacy.IfsSplit('', ' \t\n'))
    self.assertEqual(
        ['', ''], legacy.IfsSplit(' ', ' \t\n'))
    self.assertEqual(
        [''], legacy.IfsSplit('', ' '))

    # No word splitting when no IFS.  Hm.
    self.assertEqual(
        [''], legacy.IfsSplit('', ''))

  def testIfsSplit(self):
    self.assertEqual(
        ['', 'foo', 'bar', ''],
        legacy.IfsSplit('\tfoo bar\n', ' \t\n'))

    self.assertEqual(
        ['\tfoo bar\n'],
        legacy.IfsSplit('\tfoo bar\n', ''))

    self.assertEqual(
        ['a', '', 'd'],
        legacy.IfsSplit('abcd', 'bc'))


if __name__ == '__main__':
  unittest.main()
