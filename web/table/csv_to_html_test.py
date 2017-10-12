#!/usr/bin/python -S
"""
csv_to_html_test.py: Tests for csv_to_html.py
"""

import unittest

import csv_to_html  # module under test


class CsvToHtmlTest(unittest.TestCase):

  def testParseSpec(self):
    self.assertEqual(
        {'foo': 'bar', 'spam': 'eggs'},
        csv_to_html.ParseSpec(['foo bar', 'spam eggs']))

    self.assertEqual(
        {},
        csv_to_html.ParseSpec([]))


if __name__ == '__main__':
  unittest.main()
