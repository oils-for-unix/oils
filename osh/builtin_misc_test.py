#!/usr/bin/env python2
"""
builtin_misc_test.py: Tests for builtin_misc.py
"""
from __future__ import print_function

import unittest

from core import pyutil
from frontend import flag_def  # side effect: flags are defined!
_ = flag_def
from osh import split
from osh import builtin_misc  # module under test


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
      builtin_misc._AppendParts(line, spans, max_results, False, parts)
      strs = [buf.getvalue() for buf in parts]
      self.assertEqual(expected_parts, strs)

      print('---')

  def testPrintHelp(self):
    # Localization: Optionally  use GNU gettext()?  For help only.  Might be
    # useful in parser error messages too.  Good thing both kinds of code are
    # generated?  Because I don't want to deal with a C toolchain for it.

    loader = pyutil.GetResourceLoader()
    builtin_misc.Help([], loader)

if __name__ == '__main__':
  unittest.main()
