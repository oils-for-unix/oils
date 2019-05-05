#!/usr/bin/python -S
"""
builtin_test.py: Tests for builtin.py
"""
from __future__ import print_function

import unittest
import sys

from core import pyutil
from osh import split
from osh import builtin  # module under test


class BuiltinTest(unittest.TestCase):

  def testAppendParts(self):
    # allow_escape is True by default, but False when the user passes -r.
    CASES = [
        (['Aa', 'b', ' a b'], 100, 'Aa b \\ a\\ b'),
        (['a', 'b', 'c'], 3, 'a b c '),
    ]

    for expected_parts, max_results, line in CASES:
      sp = split.IfsSplitter(split.DEFAULT_IFS, '')
      spans = sp.Split(line, True)
      print('--- %r' % line)
      for span in spans:
        print('  %s %s' % span)

      parts = []
      builtin._AppendParts(line, spans, max_results, False, parts)
      self.assertEqual(expected_parts, parts)

      print('---')

  def testPrintHelp(self):
    # Localization: Optionally  use GNU gettext()?  For help only.  Might be
    # useful in parser error messages too.  Good thing both kinds of code are
    # generated?  Because I don't want to deal with a C toolchain for it.

    loader = pyutil.GetResourceLoader()
    builtin.Help([], loader)

    for name, spec in builtin.BUILTIN_DEF.arg_specs.iteritems():
      print(name)
      spec.PrintHelp(sys.stdout)
      print()


if __name__ == '__main__':
  unittest.main()
