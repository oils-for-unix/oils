#!/usr/bin/env python2
"""
web_test.py: Tests for web.py
"""
from __future__ import print_function

import unittest

from soil import web  # module under test


class WebTest(unittest.TestCase):

  def testParse(self):
    print(web._ParsePullTime('real 19.99'))

  def testTemplates(self):
    print(web.HTML_BODY_TOP_T.expand({'title': 'title & other'}))

    job = {
        'job_num': '123',
        'job_url': 'https://yo',
        'git-branch': 'soil-staging',
        'run_wwz_path': 'dev-minimal.wwz',
        'index_run_url': '123/',

        'job-name': 'dev-minimal',
        'start_time_str': '2:22',
        'pull_time_str': '1:00',
        'run_time_str': '2:00',

        'details-url': '1234/',

        'GITHUB_RUN_NUMBER': '1234',

        'run_tsv_path': 'tsv',
        'run_json_path': 'json',
        'run_wwz_path': 'wwz',
        }

    jobs = [job]

    jobs.sort(key=web.ByGithubRun, reverse=True)
    groups = web.GroupJobs(jobs, web.ByGithubRun)

    web.PrintIndexHtml('title', groups)

    web.PrintRunHtml('title', jobs)


if __name__ == '__main__':
  unittest.main()
