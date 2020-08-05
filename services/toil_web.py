#!/usr/bin/env python2
"""
toil_web.py

Each job assigned an ID.  THe job generates:

- $ID.json  # metadata
- $ID.tsv   # benchmarks/time.py output.  Success/failure for each task.
- $ID.wwz   # files

This script generates an index.html with a table of metadata and links to the
logs.

TODO:
- Use JSON Template to escape HTML
- Can we publish spec test numbers in JSON?
"""
from __future__ import print_function

import csv
import datetime
import json
import itertools
import os
import sys
from doctools import html_head


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


# *** UNUSED because it only makes sense on a dynamic web page! ***
# Loosely based on
# https://stackoverflow.com/questions/1551382/user-friendly-time-format-in-python

SECS_IN_DAY = 86400


def PrettyTime(now, start_time):
  """
  Return a pretty string like 'an hour ago', 'Yesterday', '3 months ago', 'just
  now', etc
  """
  delta = now - start_time

  if delta < 10:
      return "just now"
  if delta < 60:
      return "%d seconds ago" % delta
  if delta < 120:
      return "a minute ago"
  if delta < 3600:
      return "%d minutes ago" % (delta // 60)
  if delta < 7200:
      return "an hour ago"
  if delta < SECS_IN_DAY:
      return "%d hours ago" % (delta // 3600)

  if delta < 2 * SECS_IN_DAY:
      return "Yesterday"
  if delta < 7 * SECS_IN_DAY:
      return "%d days ago" % (delta // SECS_IN_DAY)

  if day_diff < 31 * SECS_IN_DAY:
      return "%d weeks ago" % (delta / SECS_IN_DAY / 7)

  if day_diff < 365:
      return "%d months ago" % (delta / SECS_IN_DAY / 30) 

  return "%d years ago" % (delta / SECS_IN_DAY / 365)


def ParseJobs(stdin):
  for line in stdin:
    json_path = line.strip()

    log('%s', json_path)

    with open(json_path) as f:
      meta = json.load(f)
    #print(meta)

    tsv_path = json_path[:-5] + '.tsv'
    log('%s', tsv_path)

    failed_tasks = []
    total_elapsed = 0.0
    num_tasks = 0

    with open(tsv_path) as f:
      reader = csv.reader(f, delimiter='\t')

      for row in reader:
        status = int(row[0])
        task_name = row[2]
        if status != 0:
          failed_tasks.append(task_name)

        elapsed = float(row[1])
        total_elapsed += elapsed

        num_tasks += 1

    num_failures = len(failed_tasks)
    if num_failures == 0:
      s_html = '<span class="pass">pass</span>'
    else:
      if num_failures == 1:
        fail_html = 'task <code>%s</code>' % failed_tasks[0]
      else:
        fail_html = '%d of %d tasks' % (num_failures, num_tasks)
      s_html = '<span class="fail">FAIL</span><br/><span class="fail-detail">%s</span>' % fail_html
    meta['status_html'] = s_html

    total_elapsed = int(total_elapsed)
    minutes = total_elapsed / 60
    seconds = total_elapsed % 60
    meta['elapsed_str'] = '%d:%02d' % (minutes, seconds)

    # Note: this isn't a Unix timestamp
    #microseconds = int(meta['TRAVIS_TIMER_START_TIME']) / 1e6
    #log('ts = %d', microseconds)

    start_time = meta.get('task-run-start-time')
    if start_time is None:
      start_time_str = '?'
    else:
      # Note: this is different clock!  Could be desynchronized.
      # Doesn't make sense this is static!
      #now = time.time()
      start_time = int(start_time)

      t = datetime.datetime.fromtimestamp(start_time)
      # %-I avoids leading 0, and is 12 hour date.
      # lower() for 'pm' instead of 'PM'.
      start_time_str = t.strftime('%-m/%d at %-I:%M%p').lower()

      #start_time_str = PrettyTime(now, start_time)

    meta['start_time_str'] = start_time_str

    # Metadata for "Build".  Travis has this concept, but sourcehut doesn't.
    # A build consists of many jobs.
    meta['git-branch'] = meta.get('TRAVIS_BRANCH') or '?'  # no data for sr.ht
    meta['commit-line'] = meta.get('commit-line') or '?'
    meta['commit-hash'] = meta.get('commit-hash') or '?'

    meta['commit_hash_short'] = meta['commit-hash'][-8:]  # last 8 chars

    # Metadata for "Job"

    meta['job-name'] = meta.get('job-name') or '?'  # Also TRAVIS_JOB_NAME
    meta['job_num'] = meta.get('TRAVIS_JOB_NUMBER') or meta.get('JOB_ID') or '?'
    meta['job_url'] = meta.get('TRAVIS_JOB_WEB_URL') or meta.get('JOB_URL') or '?'

    filename = os.path.basename(json_path)
    basename, _ = os.path.splitext(filename)
    meta['basename'] = basename
    yield meta


BUILD_ROW_TEMPLATE = '''\
<tr class="spacer">
  <td colspan=5></td>
</tr>
<tr class="commit-row">
  <td colspan=2>
    <code>%(git-branch)s</code>
    &nbsp;
    <code><a href="https://github.com/oilshell/oil/commit/%(commit-hash)s">%(commit_hash_short)s</a></code>
  </td>
  <td class="commit-line" colspan=3>
    <code>%(commit-line)s</code>
  </td>
</tr>
<tr class="spacer">
  <td colspan=5><td/>
</tr>
'''


JOB_ROW_TEMPLATE = '''\
<tr>
  <td>%(job_num)s</td>
  <td> <code><a href="%(basename)s.wwz/">%(job-name)s</a></code> </td>
  <td><a href="%(job_url)s">%(start_time_str)s</a></td>
  <td>%(elapsed_str)s</td>
  <td>%(status_html)s</td>
  <!-- todo; spec details
  <td> </td>
  -->
</tr>
'''

INDEX_TOP = '''
  <body class="width50">
    <p id="home-link">
      <a href="/">travis-ci.oilshell.org</a>
      | <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>Recent Jobs</h1>

    <table>
      <thead>
        <tr>
          <td>Job #</td>
          <td>Job Name</td>
          <td>Start Time</td>
          <td>Elapsed</td>
          <td>Status</td>
          <!--
          <td>Details</td>
          -->
        </tr>
      </thead>
'''

INDEX_BOTTOM = '''\
    </table>

    <p>
      <a href="raw.html">raw data</a>
    </p>
  </body>
</html>
'''

# Sort by descending build number
def ByBuildNum(row):
  return int(row.get('TRAVIS_BUILD_NUMBER', 0))

def ByTaskRunStartTime(row):
  return int(row.get('task-run-start-time', 0))

def ByCommitDate(row):
  # This is in ISO 8601 format (git log %aI), so we can sort by it.
  return row.get('commit-date', '?')


def main(argv):
  action = argv[1]

  if action == 'srht-index':

    # Bust cache (e.g. Safari iPad seems to cache aggressively and doesn't
    # have Ctrl-F5)
    html_head.Write(sys.stdout, 'Recent Jobs',
        css_urls=['../web/base.css?cache=0', '../web/toil.css?cache=0'])

    print(INDEX_TOP)

    rows = list(ParseJobs(sys.stdin))

    # sourcehut doesn't have this grouping.
    rows.sort(key=ByCommitDate, reverse=True)
    groups = itertools.groupby(rows, key=ByCommitDate)

    for commit_hash, group in groups:
      jobs = list(group)
      # Sort by start time
      jobs.sort(key=ByTaskRunStartTime, reverse=True)

      # First job
      print(BUILD_ROW_TEMPLATE % jobs[0])

      for job in jobs:
        print(JOB_ROW_TEMPLATE % job)

    print(INDEX_BOTTOM)
    log('srht-index done')

  elif action == 'travis-index':

    # Bust cache (e.g. Safari iPad seems to cache aggressively and doesn't
    # have Ctrl-F5)
    html_head.Write(sys.stdout, 'Recent Jobs',
        css_urls=['../web/base.css?cache=0', '../web/toil.css?cache=0'])

    print(INDEX_TOP)
    rows = list(ParseJobs(sys.stdin))

    rows.sort(key=ByBuildNum, reverse=True)
    groups = itertools.groupby(rows, key=ByBuildNum)
    #print(list(groups))

    for build_num, group in groups:
      build_num = int(build_num)
      log('build %d', build_num)

      jobs = list(group)

      # Sort by start time
      jobs.sort(key=ByTaskRunStartTime, reverse=True)

      # The first job should have the same branch/commit/commit_line
      print(BUILD_ROW_TEMPLATE % jobs[0])

      for job in jobs:
        print(JOB_ROW_TEMPLATE % job)

    print(INDEX_BOTTOM)

  elif action == 'cleanup':
    prefixes = []
    for line in sys.stdin:
      json_path = line.strip()

      log('%s', json_path)
      prefixes.append(json_path[:-5])

    # looks like 2020-03-20, so sort ascending means the oldest are first
    prefixes.sort()

    # Keep 200 jobs.  We only display the last 100.
    prefixes = prefixes[:-200]

    # Show what to delete.  Then the user can pipe to xargs rm to remove it.
    for prefix in prefixes:
      print(prefix + '.json')
      print(prefix + '.tsv')
      print(prefix + '.wwz')

  else:
    raise RuntimeError('Invalid action %r' % action)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
