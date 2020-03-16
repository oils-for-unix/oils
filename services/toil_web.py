#!/usr/bin/env python2
"""
toil_index.py

Each continuous build run is assigned an ID.  Then it will generate:

- $ID.git-log 
- $ID.json  # metadata
- $ID.tsv   # benchmarks/time.py output?  success/failure for each task
- $ID.wwz   # files

This script should generate an index.html with links to all the logs.

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

    # Note: this isn't what I think it is
    #microseconds = int(meta['TRAVIS_TIMER_START_TIME']) / 1e6
    #log('ts = %d', microseconds)
    d = datetime.datetime.now()
    meta['start_time_str'] = d.strftime('TODO')

    meta['commit_line'] = meta['TRAVIS_COMMIT_MESSAGE'].splitlines()[0]
    meta['commit_hash'] = meta['TRAVIS_COMMIT'][-8:]  # last 8 chars

    filename = os.path.basename(json_path)
    basename, _ = os.path.splitext(filename)
    meta['basename'] = basename
    yield meta


# TODO:
# - Use JSON Template to escape it
# - Red/Green for pass/fail from spec tests

ROW_TEMPLATE = '''
<tr class="commit-row" style="padding-top: 1em">
  <td> <code>%(TRAVIS_BRANCH)s</code> </td>
  <td> <code>%(commit_hash)s</code> </td>
  <td colspan="4">%(commit_line)s</td>
</tr>
<tr>
  <td>%(max_status)d</td>
  <td>%(start_time_str)s</td>
  <td>%(total_elapsed).2f</td>
  <td>%(TRAVIS_JOB_NAME)s</td>
  <td><a href="%(TRAVIS_JOB_WEB_URL)s">%(TRAVIS_JOB_NUMBER)s</a></td>
  <td><a href="%(basename)s.wwz/">Details</a></td>
</tr>
'''


def main(argv):
  action = argv[1]

  if action == 'index':

    html_head.Write(sys.stdout, 'Recent Jobs',
        css_urls=['../web/base.css', '../web/toil.css'])

    print('''
  <body class="width40">
    <p id="home-link">
      <a href="/">travis-ci.oilshell.org</a>
      | <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>Recent Jobs</h1>

    <p>
      <a href="raw.html">raw data</a>
    </p>

    <table>
      <thead>
        <tr>
          <td>Status</td>
          <td>Start Time</td>
          <td>Elapsed</td>
          <td>Job Name</td>
          <td>Job ID</td>
          <td>Details</td>
        </tr>
      </thead>
''')

    # TODO:
    # - Group by git commit
    # - Show description and escape it

    rows = list(ParseJobs(sys.stdin))
    rows.sort(
        key=lambda row: int(row['TRAVIS_TIMER_START_TIME']), reverse=True)

    for row in rows:
      print(ROW_TEMPLATE % row)

    print('''\
    </table>
  </body>
</html>
  ''')

    # TODO: read jobs on stdin
    # - open .tsv and JSON
    # - write HTML to output

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
