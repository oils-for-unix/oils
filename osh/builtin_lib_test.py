#!/usr/bin/env python2
"""
builtin_lib_test.py: Tests for builtin_lib.py
"""
from __future__ import print_function

import cStringIO
import unittest
# We use native/line_input.c, a fork of readline.c, but this is good enough for
# unit testing
import readline

from core import test_lib
from frontend import flag_def  # side effect: flags are defined!
_ = flag_def
from osh import builtin_lib  # module under test


class BuiltinTest(unittest.TestCase):
  TEST_PATH = '_tmp/builtin_test_history.txt'


  def _readHistFile(self):
     # type: (self) -> str
     with open(BuiltinTest.TEST_PATH, 'r') as hist_file:
        return hist_file.read()


  def testHistoryBuiltin(self):
     with open(BuiltinTest.TEST_PATH, 'w') as f:
       f.write("""\
echo hello
ls one/
ls two/
echo bye
""")
     readline.read_history_file(BuiltinTest.TEST_PATH)

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
    
     _TestHistory(['history', '-d', '4'])

     # Call history
     out = _TestHistory(['history'])

     # Note: whitespace here is exact
     self.assertEqual(out, """\
    1  echo hello
    2  ls one/
    3  ls two/
""")

     # Append current history to history file.
     # This functionality is *silent*, so we
     # need to read the history file to test
     # the assertion.

     # No change to history file before `history -a`
     self.assertEqual(self._readHistFile(), """\
echo hello
ls one/
ls two/
echo bye
""")

     _TestHistory(['history', '-a'])

     # After history -a, the history file will have changed
     self.assertEqual(self._readHistFile(), """\
echo hello
ls one/
ls two/
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
   b = builtin_lib.History(readline, BuiltinTest.TEST_PATH, f)
   cmd_val = test_lib.MakeBuiltinArgv(argv)
   b.Run(cmd_val)
   return f.getvalue()


if __name__ == '__main__':
  unittest.main()
