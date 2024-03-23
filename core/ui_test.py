#!/usr/bin/env python2
from __future__ import print_function
"""ui_test.py: Tests for ui.py."""

import unittest

from core import test_lib
from core import ui  # module under test


class UiTest(unittest.TestCase):

    def testErrorFormatter(self):
        arena = test_lib.MakeArena('')
        line_id = arena.AddLine('[line one]', 1)
        tok1 = arena.NewToken(-1, 0, 2, line_id)
        tok2 = arena.NewToken(-1, 2, 2, line_id)

        errfmt = ui.ErrorFormatter()

        # no location info
        errfmt.Print_('hello')

        with ui.ctx_Location(errfmt, tok1):
            errfmt.Print_('zero')
            errfmt.Print_('zero', tok2)


if __name__ == '__main__':
    unittest.main()
