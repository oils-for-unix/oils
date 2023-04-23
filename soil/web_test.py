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

    d = {
        'job_num': '123',
        'wwz_path': '123/dev-minimal.wwz',
        'job-name': 'dev-minimal',
        'start_time_str': '2:22',
        'pull_time_str': '1:00',
        'run_time_str': '2:00',
        }
    print(web.JOB_ROW_TEMPLATE.expand(d))


if __name__ == '__main__':
  unittest.main()
