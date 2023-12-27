#!/usr/bin/env python2
from __future__ import print_function

import unittest

from core import pyutil
try:
    from _devbuild.gen.help_meta import TOPICS
except ImportError:
    TOPICS = None  # minimal dev build

from builtin import misc_osh  # module under test


class BuiltinTest(unittest.TestCase):

    def testPrintHelp(self):
        # Localization: Optionally  use GNU gettext()?  For help only.  Might be
        # useful in parser error messages too.  Good thing both kinds of code are
        # generated?  Because I don't want to deal with a C toolchain for it.

        loader = pyutil.GetResourceLoader()
        errfmt = None
        misc_osh.Help('ysh', loader, TOPICS, errfmt)


if __name__ == '__main__':
    unittest.main()
