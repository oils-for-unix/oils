#!/usr/bin/env python2
"""
web_test.py: Tests for web.py
"""
from __future__ import print_function

import itertools
import unittest

from soil import web  # module under test


class WebTest(unittest.TestCase):

  def testParse(self):
    print(web._ParsePullTime(None))
    print(web._ParsePullTime('real 19.99'))

  def testTemplates(self):
    print(web.INDEX_TOP.expand({'title': 'title & other'}))

    job = {
        'job_num': '123',
        'job_url': 'https://yo',
        'git-branch': 'soil-staging',
        'wwz_path': '123/dev-minimal.wwz',
        'job-name': 'dev-minimal',
        'start_time_str': '2:22',
        'pull_time_str': '1:00',
        'run_time_str': '2:00',

        'GITHUB_RUN_NUMBER': '1234',
        }
    print(web.JOB_ROW_TEMPLATE.expand(job))

    rows = [job]

    rows.sort(key=web.ByGithub, reverse=True)
    groups = itertools.groupby(rows, key=web.ByGithub)

    web.PrintJobHtml('title', groups)


if __name__ == '__main__':
  unittest.main()
