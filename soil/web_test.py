#!/usr/bin/env python2
"""
web_test.py: Tests for web.py
"""
from __future__ import print_function

import unittest

import web  # module under test


class WebTest(unittest.TestCase):

  def testParse(self):
    print(web._ParsePullTime(None))
    print(web._ParsePullTime('real 19.99'))

  def testTemplates(self):
    print(web.IndexTop('title & other'))

if __name__ == '__main__':
  unittest.main()
