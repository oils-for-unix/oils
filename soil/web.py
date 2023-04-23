#!/usr/bin/env python2
"""
soil/web.py

Each job is assigned an ID.  The job generates:

- $ID.json  # metadata
- $ID.tsv   # benchmarks/time.py output.  Success/failure for each task.
- $ID.wwz   # files

This script generates an index.html with a table of metadata and links to the
logs.

TODO:
- Use JSON Template to escape HTML
- Can we publish spec test numbers in JSON?

How to test changes to this file:

  $ soil/web-init.sh deploy-code
  $ soil/github-actions.sh remote-rewrite-jobs-index github-

"""
from __future__ import print_function

import cgi
import csv
import datetime
import json
import itertools
import os
import re
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


def _MinutesSeconds(num_seconds):
  num_seconds = round(num_seconds)  # round to integer
  minutes = num_seconds / 60
  seconds = num_seconds % 60
  return '%d:%02d' % (minutes, seconds)


LINE_RE = re.compile(r'(\w+)[ ]+([\d.]+)')

def _ParsePullTime(time_p_str):
  """
  Given time -p output like

  real 0.01
  user 0.02
  sys 0.02

  Return the real time as a string, or - if we don't know it.
  """
  if time_p_str is None:
    return '-'

  for line in time_p_str.splitlines():
    m = LINE_RE.match(line)
    if m:
      name, value = m.groups()
      if name == 'real':
        return _MinutesSeconds(float(value))

  return '-'  # Not found


def ParseJobs(stdin):
  for i, line in enumerate(stdin):
    json_path = line.strip()

    #if i % 20 == 0:
    #  log('job %d = %s', i, json_path)

    with open(json_path) as f:
      meta = json.load(f)
    #print(meta)

    tsv_path = json_path[:-5] + '.tsv'
    #log('%s', tsv_path)

    failed_tasks = []
    total_elapsed = 0.0
    num_tasks = 0

    with open(tsv_path) as f:
      reader = csv.reader(f, delimiter='\t')

      try:
        for row in reader:
          status = int(row[0])
          task_name = row[2]
          if status != 0:
            failed_tasks.append(task_name)

          elapsed = float(row[1])
          total_elapsed += elapsed

          num_tasks += 1
      except (IndexError, ValueError) as e:
        raise RuntimeError('Error in %r: %s (%r)' % (tsv_path, e, row))

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

    meta['run_time_str'] = _MinutesSeconds(total_elapsed)

    meta['pull_time_str'] = _ParsePullTime(meta.get('image-pull-time'))

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

    # Metadata for a "build".  A build consists of many jobs.

    github_branch = meta.get('GITHUB_REF') 
    branch_str = github_branch or '?'  # no data for sr.ht

    # Show the branch ref/heads/soil-staging or ref/pull/1577/merge (linkified)
    pr_number = meta.get('GITHUB_PR_NUMBER')
    if pr_number and github_branch:

      # pr_number from YAML will be '1577'
      # branch from Github should be 'ref/pull/1577/merge'
      to_highlight = 'pull/%s' % pr_number
      assert to_highlight in github_branch, \
          "%r doesn't contain %r" % (github_branch, to_highlight)

      linkified = '<code><a href="https://github.com/oilshell/oil/pull/%s">%s</a></code>' % (
          pr_number, to_highlight)
      meta['git-branch-html'] = github_branch.replace(to_highlight, linkified)
    else:
      meta['git-branch-html'] = cgi.escape(branch_str)

    github_pr_head_ref = meta.get('GITHUB_PR_HEAD_REF')

    if github_pr_head_ref:
      ref_url = 'https://github.com/oilshell/oil/tree/%s' % github_pr_head_ref
      meta['description-html'] = 'PR from <a href="%s">%s</a> updated' % (
          ref_url, github_pr_head_ref)

      # Show the user's commit, not the merge commit
      meta['commit-hash'] = meta.get('GITHUB_PR_HEAD_SHA') or '?'

    else:
      # From soil/worker.sh save-metadata.  This is intended to be
      # CI-independent, while the environment variables above are from Github.
      meta['description-html'] = cgi.escape(meta.get('commit-line', '?'))
      meta['commit-hash'] = meta.get('commit-hash') or '?'

    meta['commit_hash_short'] = meta['commit-hash'][-8:]  # last 8 chars

    # Metadata for "Job"

    meta['job-name'] = meta.get('job-name') or '?'  # Also TRAVIS_JOB_NAME
    meta['job_num'] = meta.get('TRAVIS_JOB_NUMBER') or meta.get('JOB_ID') or meta.get('GITHUB_RUN_ID') or '?'
    # For Github, we construct $JOB_URL in soil/github-actions.sh
    meta['job_url'] = meta.get('TRAVIS_JOB_WEB_URL') or meta.get('JOB_URL') or '?'

    filename = os.path.basename(json_path)
    basename, _ = os.path.splitext(filename)
    meta['basename'] = basename
    yield meta


BUILD_ROW_TEMPLATE = '''\
<tr class="spacer">
  <td colspan=6></td>
</tr>
<tr class="commit-row">
  <td colspan=2>
    <code>%(git-branch-html)s</code>
    &nbsp;
    <code><a href="https://github.com/oilshell/oil/commit/%(commit-hash)s">%(commit_hash_short)s</a></code>
  </td>
  <td class="commit-line" colspan=4>
    <code>%(description-html)s</code>
  </td>
</tr>
<tr class="spacer">
  <td colspan=6><td/>
</tr>
'''


JOB_ROW_TEMPLATE = '''\
<tr>
  <td>%(job_num)s</td>
  <td> <code><a href="%(basename)s.wwz/">%(job-name)s</a></code> </td>
  <td><a href="%(job_url)s">%(start_time_str)s</a></td>
  <td>%(pull_time_str)s</td>
  <td>%(run_time_str)s</td>
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

    <h1>%(title)s</h1>

    <table>
      <thead>
        <tr>
          <td>Job #</td>
          <td>Job Name</td>
          <td>Start Time</td>
          <td>Pull Time</td>
          <td>Run Time</td>
          <td>Status</td>
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
def ByTravisBuildNum(row):
  return int(row.get('TRAVIS_BUILD_NUMBER', 0))

def ByTaskRunStartTime(row):
  return int(row.get('task-run-start-time', 0))

def ByCommitDate(row):
  # Written in the shell script
  # This is in ISO 8601 format (git log %aI), so we can sort by it.
  return row.get('commit-date', '?')

def ByCommitHash(row):
  return row.get('commit-hash', '?')

def ByGithub(row):
  # Written in the shell script
  # This is in ISO 8601 format (git log %aI), so we can sort by it.
  return int(row.get('GITHUB_RUN_ID', 0))


def HtmlHead(title):
  # Bust cache (e.g. Safari iPad seems to cache aggressively and doesn't
  # have Ctrl-F5)
  html_head.Write(sys.stdout, title,
      css_urls=['../web/base.css?cache=0', '../web/soil.css?cache=0'])


def IndexTop(title):
  d = {'title': cgi.escape(title)}
  print(INDEX_TOP % d)


def main(argv):
  action = argv[1]

  if action == 'srht-index':
    title = 'Recent Jobs (sourcehut)'
    HtmlHead(title)
    IndexTop(title)

    rows = list(ParseJobs(sys.stdin))

    # sourcehut doesn't have a build number.
    # - Sort by commit date.  (Minor problem: Committing on a VM with bad block
    #   can cause commits "in the past")
    # - Group by commit hash.  Because 'git rebase' can cause two different
    # commits with the same date.
    rows.sort(key=ByCommitDate, reverse=True)
    groups = itertools.groupby(rows, key=ByCommitHash)

    for commit_hash, group in groups:
      jobs = list(group)
      # Sort by start time
      jobs.sort(key=ByTaskRunStartTime, reverse=True)

      # First job
      print(BUILD_ROW_TEMPLATE % jobs[0])

      for job in jobs:
        print(JOB_ROW_TEMPLATE % job)

    print(INDEX_BOTTOM)

  elif action == 'github-index':
    title = 'Recent Jobs (Github Actions)'
    HtmlHead(title)
    IndexTop(title)

    rows = list(ParseJobs(sys.stdin))

    rows.sort(key=ByGithub, reverse=True)
    groups = itertools.groupby(rows, key=ByGithub)

    for commit_hash, group in groups:
      jobs = list(group)
      # Sort by start time
      jobs.sort(key=ByTaskRunStartTime, reverse=True)

      # First job
      print(BUILD_ROW_TEMPLATE % jobs[0])

      for job in jobs:
        print(JOB_ROW_TEMPLATE % job)

    print(INDEX_BOTTOM)

  elif action == 'travis-index':
    title = 'Recent Jobs (Travis CI)'
    HtmlHead(title)
    IndexTop(title)

    rows = list(ParseJobs(sys.stdin))

    rows.sort(key=ByTravisBuildNum, reverse=True)
    groups = itertools.groupby(rows, key=ByTravisBuildNum)
    #print(list(groups))

    for build_num, group in groups:
      #build_num = int(build_num)
      #log('build %d', build_num)

      jobs = list(group)

      # Sort by start time
      jobs.sort(key=ByTaskRunStartTime, reverse=True)

      # The first job should have the same branch/commit/commit_line
      print(BUILD_ROW_TEMPLATE % jobs[0])

      for job in jobs:
        print(JOB_ROW_TEMPLATE % job)

    print(INDEX_BOTTOM)

  elif action == 'cleanup':
    try:
      num_to_keep = int(argv[2])
    except IndexError:
      num_to_keep = 200

    prefixes = []
    for line in sys.stdin:
      json_path = line.strip()

      #log('%s', json_path)
      prefixes.append(json_path[:-5])

    log('%s cleanup: keep %d', sys.argv[0], num_to_keep)
    log('%s cleanup: got %d JSON paths', sys.argv[0], len(prefixes))

    # looks like 2020-03-20, so sort ascending means the oldest are first
    prefixes.sort()

    prefixes = prefixes[:-num_to_keep]

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
