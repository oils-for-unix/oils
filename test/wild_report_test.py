#!/usr/bin/env python2
"""
wild_report_test.py: Tests for wild_report.py
"""

import unittest

import wild_report  # module under test


class FooTest(unittest.TestCase):
  def setUp(self):
    pass

  def tearDown(self):
    pass

  def testTemplate(self):
    BODY_STYLE = wild_report.BODY_STYLE
    PAGE_TEMPLATES = wild_report.PAGE_TEMPLATES

    data = {'base_url': '', 'failures': [], 'task': 'osh2oil'}

    body = BODY_STYLE.expand(data, group=PAGE_TEMPLATES['FAILED'])
    print(body)


if __name__ == '__main__':
  unittest.main()
