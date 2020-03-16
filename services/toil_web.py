#!/usr/bin/env python2
"""
toil_web.py

Each continuous build run is assigned an ID.  Then it will generate:

- $ID.json  # metadata
- $ID.tsv   # benchmarks/time.py output?  success/failure for each task
- $ID.wwz   # files

This script generates an index.html with a table of metadata and links to the
logs.
"""
from __future__ import print_function

import csv
import datetime
import json
import os
import sys
from doctools import html_head


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def ParseJobs(stdin):
  for line in stdin:
    json_path = line.strip()

    log('%s', json_path)

    with open(json_path) as f:
      meta = json.load(f)
    #print(meta)

    tsv_path = json_path[:-5] + '.tsv'
    log('%s', tsv_path)

    max_status = 0
    total_elapsed = 0.0

    with open(tsv_path) as f:
      reader = csv.reader(f, delimiter='\t')

      for row in reader:
        status = int(row[0])
        elapsed = float(row[1])

        max_status = max(status, max_status)
        total_elapsed += elapsed

    meta['max_status'] = max_status
    meta['total_elapsed'] = total_elapsed

    # Note: this isn't a Unix timestamp
    #microseconds = int(meta['TRAVIS_TIMER_START_TIME']) / 1e6
    #log('ts = %d', microseconds)

    # TODO: We could show "X minutes ago" etc.
    d = datetime.datetime.now()
    meta['start_time_str'] = meta.get('TASK_RUN_START_TIME', '?')

    try:
      commit_line = meta['TRAVIS_COMMIT_MESSAGE'].splitlines()[0]
    except AttributeError:
      commit_line = '?'
    meta['commit_line'] = commit_line

    try:
      commit_hash = meta['TRAVIS_COMMIT'][-8:]  # last 8 chars
    except TypeError:
      commit_hash = '?'
    meta['commit_hash']  = commit_hash

    filename = os.path.basename(json_path)
    basename, _ = os.path.splitext(filename)
    meta['basename'] = basename
    yield meta


# TODO:
# - Use JSON Template to escape it
# - Red/Green for pass/fail (spec test CSS)
# - Can we publish spec test numbers in JSON?

BUILD_ROW_TEMPLATE = '''\
<tr class="spacer">
  <td colspan=5><td/>
</tr>
<tr class="commit-row">
  <td> %(TRAVIS_BUILD_NUMBER)s </td>
  <td> <code>%(TRAVIS_BRANCH)s</code> </td>
  <td>
    <code><a href="https://github.com/oilshell/oil/commit/%(TRAVIS_COMMIT)s">%(commit_hash)s</a></code>
  </td>
  <td class="commit-line" colspan="2">%(commit_line)s</td>
</tr>
<tr class="spacer">
  <td colspan=5><td/>
</tr>
'''


JOB_ROW_TEMPLATE = '''\
<tr>
  <td><a href="%(TRAVIS_JOB_WEB_URL)s">%(TRAVIS_JOB_NUMBER)s</a></td>
  <td> <code>%(TRAVIS_JOB_NAME)s</code> </td>
  <td>%(start_time_str)s</td>
  <td><a href="%(basename)s.wwz/">%(total_elapsed).2f</a></td>
  <td>%(max_status)d</td>
</tr>
'''


def main(argv):
  action = argv[1]

  if action == 'index':

    # Bust cache (e.g. Safari iPad seems to cache aggressively and doesn't
    # have Ctrl-F5)
    html_head.Write(sys.stdout, 'Recent Jobs',
        css_urls=['../web/base.css?cache=0', '../web/toil.css?cache=0'])

    print('''
  <body class="width40">
    <p id="home-link">
      <a href="/">travis-ci.oilshell.org</a>
      | <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>Recent Jobs</h1>

    <table>
      <thead>
        <!--
        <tr class="commit-row">
          <td>Build #</td>
          <td>Branch</td>
          <td>Commit</td>
          <td class="commit-line" colspan=2>Description</td>
        </tr>
        -->
        <tr>
          <td>Job #</td>
          <td>Job Name</td>
          <td>Start Time</td>
          <td>Elapsed</td>
          <td>Status</td>
        </tr>
      </thead>
''')

    rows = list(ParseJobs(sys.stdin))
    import itertools

    # Sort by descending build number
    def ByBuildNum(row):
      return int(row.get('TRAVIS_BUILD_NUMBER', 0))

    def ByTaskRunStartTime(row):
      return int(row.get('TASK_RUN_START_TIME', 0))

    rows.sort(key=ByBuildNum, reverse=True)
    groups = itertools.groupby(rows, key=ByBuildNum)
    #print(list(groups))

    for build_num, group in groups:
      build_num = int(build_num)
      log('---')
      log('build %d', build_num)

      jobs = list(group)

      # Sort by start time
      jobs.sort(key=ByTaskRunStartTime, reverse=True)

      # The first job should have the same branch/commit/commit_line
      print(BUILD_ROW_TEMPLATE % jobs[0])

      for job in jobs:
        print(JOB_ROW_TEMPLATE % job)

    print('''\
    </table>

    <p>
      <a href="raw.html">raw data</a>
    </p>
  </body>
</html>
  ''')

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
