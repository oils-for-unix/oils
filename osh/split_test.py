#!/usr/bin/env python2
"""
split.test.py: Tests for split.py
"""

import unittest

from osh import split  # module under test


def _RunSplitCases(test, sp, cases):

  for expected_parts, s, allow_escape in cases:
    spans = sp.Split(s, allow_escape)
    if 0:
      print('%r: %s' % (s, spans))
    else:
      # Verbose for debugging
      print(repr(s))
      for span in spans:
        print('  %s %s' % span)

    parts = split._SpansToParts(s, spans)
    print('PARTS %s' % parts)

    test.assertEqual(expected_parts, parts,
        '%r: %s != %s' % (s, expected_parts, parts))


class SplitTest(unittest.TestCase):

  def testSpansToParts(self):
    sp = split.IfsSplitter(split.DEFAULT_IFS, '')

    s = 'one\\ two'
    spans = sp.Split(s, False)
    print(spans)

    parts = split._SpansToParts(s, spans)
    self.assertEqual(['one\\', 'two'], parts)

    spans = sp.Split(s, True)  # allow_escape
    parts = split._SpansToParts(s, spans)
    self.assertEqual(['one two'], parts)

    # NOTE: Only read builtin supports max_results
    return

    parts = split._SpansToParts(s, spans, max_results=1)
    self.assertEqual(['one\\ two'], parts)

    print(spans)

    parts = split._SpansToParts(s, spans, max_results=1)
    self.assertEqual(['one two'], parts)

  def testTrailingWhitespaceBug(self):
    # Bug: these differed
    CASES = [
        (['x y'], r' x\ y', True),
        (['ab '], r' ab\ ', True),
        (['ab '], r' ab\  ', True),
    ]
    sp = split.IfsSplitter(split.DEFAULT_IFS, '')
    _RunSplitCases(self, sp, CASES)

  def testDefaultIfs(self):
    CASES = [
        ([], '', True),
        (['a'], 'a', True),
        (['a'], ' a ', True),
        (['ab'], '\tab\n', True),
        (['a', 'b'], 'a  b\n', True),

        (['a b'], r'a\ b', True),
        (['a\\', 'b'], r'a\ b', False),

        ([r'\*.sh'], r'\\*.sh', True),

        (['Aa', 'b', ' a b'], 'Aa b \\ a\\ b', True),
    ]

    sp = split.IfsSplitter(split.DEFAULT_IFS, '')
    _RunSplitCases(self, sp, CASES)

    self.assertEqual(r'a\ _b', sp.Escape('a _b'))

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

        # NOTES:
        # - This cases REQUIRES ignoring leading whitespace.  The state machine
        # can't handle it.  Contrast with the case above.
        # - We get three spans with index 1 because of the initial rule to
        # ignore whitespace, and then EMIT_EMPTY.  Seems harmless for now?
        (['', 'a'], ' _ a _ ', True),

        # Backslash escape
        (['a b'], r'a\ b', True),
        (['a\\', 'b'], r'a\ b', False),
    ]

    # IFS='_ '
    sp = split.IfsSplitter(' ', '_')
    _RunSplitCases(self, sp, CASES)

    self.assertEqual('a\ \_b', sp.Escape('a _b'))

  def testWhitespaceOnly(self):
    CASES = [
        ([], '', True),
        ([], '\t', True),
        (['a'], 'a\t', True),
        (['a', 'b'], '\t\ta\tb\t', True),

        # Backslash escape
        (['a\tb'], 'a\\\tb', True),
        (['a\\', 'b'], 'a\\\tb', False),
    ]

    # IFS='_ '
    sp = split.IfsSplitter('\t', '')
    _RunSplitCases(self, sp, CASES)

    self.assertEqual('a b', sp.Escape('a b'))
    self.assertEqual('a\\\tb', sp.Escape('a\tb'))

  def testOtherOnly(self):
    CASES = [
        ([], '', True),
        ([''], '_', True),
        (['a'], 'a_', True),
        (['', '', 'a', 'b'], '__a_b_', True),

        # Backslash escape
        (['a_b'], r'a\_b', True),
        (['a\\', 'b'], r'a\_b', False),
    ]

    # IFS='_ '
    sp = split.IfsSplitter('', '_')
    _RunSplitCases(self, sp, CASES)

  def testTwoOther(self):
    CASES = [
        (['a', '', 'b', '', '', 'c', 'd'], 'a__b---c_d', True),

        # Backslash escape
        (['a_-b'], r'a\_\-b', True),
        (['a\\', '\\', 'b'], r'a\_\-b', False),
    ]

    # IFS='_ '
    sp = split.IfsSplitter('', '_-')
    _RunSplitCases(self, sp, CASES)


if __name__ == '__main__':
  unittest.main()
