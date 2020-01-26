#!/usr/bin/env python2
"""
builtin_test.py: Tests for builtin.py
"""
from __future__ import print_function

import cStringIO
import unittest
# We use native/line_input.c, a fork of readline.c, but this is good enough for
# unit testing
import readline
import sys

from core import pyutil
from core import test_lib
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

  def testHistoryBuiltin(self):
     test_path = '_tmp/builtin_test_history.txt'
     with open(test_path, 'w') as f:
       f.write("""
echo hello
ls one/
ls two/
echo bye
""")
     readline.read_history_file(test_path)

     # Show all
     f = cStringIO.StringIO()
     out = _TestHistory(['history'])

     self.assertEqual(out, """\
    1  echo hello
    2  ls one/
    3  ls two/
    4  echo bye
""")

     # Show two history items
     out = _TestHistory(['history', '2'])
     # Note: whitespace here is exact
     self.assertEqual(out, """\
    3  ls two/
    4  echo bye
""")

    
     # Delete single history item.
     # This functionlity is *silent*
     # so call history again after 
     # this to feed the test assertion
    
     _TestHistory(['history', '-d', '4' ])

     # Call history
     out = _TestHistory(['history'])

     # Note: whitespace here is exact
     self.assertEqual(out, """\
    1  echo hello
    2  ls one/
    3  ls two/
""")


     # Clear history
     # This functionlity is *silent*
     # so call history again after 
     # this to feed the test assertion

     _TestHistory(['history', '-c'])

     # Call history
     out = _TestHistory(['history'])

     self.assertEqual(out, """\
""")


def _TestHistory(argv):
   f = cStringIO.StringIO()
   b = builtin.History(readline, f=f)
   cmd_val = test_lib.MakeBuiltinArgv(argv)
   b(cmd_val)
   return f.getvalue()


if __name__ == '__main__':
  unittest.main()
