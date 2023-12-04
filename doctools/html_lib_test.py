#!/usr/bin/env python2
from __future__ import print_function

import unittest

from doctools import html_lib


class FunctionsTest(unittest.TestCase):

  def testPrettyHref(self):
    self.assertEqual('foo-bar', html_lib.PrettyHref('foo  bar', False))
    self.assertEqual('why-not', html_lib.PrettyHref('Why Not??', False))
    self.assertEqual('cant-touch-this', html_lib.PrettyHref("Can't Touch This!", False))

    self.assertEqual('foo-bar', html_lib.PrettyHref('foo  bar', True))
    self.assertEqual('Why-Not', html_lib.PrettyHref('Why Not??', True))
    self.assertEqual('Cant-Touch-This', html_lib.PrettyHref("Can't Touch This!", True))

    # This is what github does:
    if 0:
      self.assertEqual('section-2--3', html_lib.PrettyHref("Section 2 + 3"))
      self.assertEqual('break--return--continue', html_lib.PrettyHref("break / return / continue"))
      self.assertEqual('inside-', html_lib.PrettyHref('Inside ${}'))
    # Ours is cleaner
    else:
      self.assertEqual('section-2-3', html_lib.PrettyHref("Section 2 + 3", False))
      self.assertEqual('break-return-continue', html_lib.PrettyHref("break / return / continue", False))
      self.assertEqual('inside', html_lib.PrettyHref('Inside ${}', False))
      self.assertEqual('bash-compatible', html_lib.PrettyHref('Bash-Compatible', False))


if __name__ == '__main__':
  unittest.main()
