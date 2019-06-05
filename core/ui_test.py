#!/usr/bin/env python2
from __future__ import print_function
"""
ui_test.py: Tests for ui.py
"""

import unittest

from core import test_lib
from core import ui  # module under test


class UiTest(unittest.TestCase):

  def testStderr(self):
    ui.Stderr('oops')

  def testErrorFormatter(self):
    arena = test_lib.MakeArena('')
    line_id = arena.AddLine('[line one]', 1)
    span_id = arena.AddLineSpan(line_id, 0, 2)
    spid1 = arena.AddLineSpan(line_id, 2, 2)

    errfmt = ui.ErrorFormatter(arena)

    # no location info
    errfmt.Print('hello')

    errfmt.PushLocation(span_id)
    errfmt.Print('zero')
    errfmt.Print('zero', span_id=spid1)


if __name__ == '__main__':
  unittest.main()
