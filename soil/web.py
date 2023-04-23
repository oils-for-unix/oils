#!/usr/bin/env python2
"""
soil/web.py - Dashboard using "Event Sourcing" Paradigm

Given this state:

https://test.oils-for-unix.org/
  github-jobs/
    1234/  # $GITHUB_RUN_NUMBER
      cpp-small.tsv    # benchmarks/time.py output.  Success/failure for each task.
      cpp-small.json   # metadata when job is DONE
      cpp-small.state  # for more transient events

      (cpp-small.wwz is linked to, but not part of the state.)

This script generates:

https://test.oils-for-unix.org/
  github-jobs/
    1234/
      tmp-$$.index.html  # function of JSON contents
      tmp-$$.raw.html    # function of dir listing
      tmp-$$.remove.txt  # function of dir listing (JSON only)
    commits/
      tmp-$$.01ab01ab.html  # function of JSON and _tmp/soil/INDEX.tsv
                            # links to all jobs AND all tasks
                            # TODO: and all container images

TODO:
- Use JSON Template to escape HTML
- Can we publish spec test numbers in JSON?

- What about HTML generated on the WORKER?
  - foo.wwz/index.html
  - _tmp/soil/image.html - layers

How to test changes to this file:

  $ soil/web-init.sh deploy-code
  $ soil/github-actions.sh remote-rewrite-jobs-index github-

"""
from __future__ import print_function

import csv
import datetime
import json
import itertools
import os
import re
import sys
from doctools import html_head
from test import jsontemplate


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


RUN_ROW_TEMPLATE = jsontemplate.Template('''\
<tr class="spacer">
  <td colspan=6></td>
</tr>
<tr class="commit-row">
  <td colspan=2>
    <code>{git-branch}</code>
    &nbsp;
    {.section github-commit-link}
      <code>
        <a href="https://github.com/oilshell/oil/commit/{commit-hash}">{commit-hash-short}</a>
      </code>
    {.end}
  </td>

  <td class="commit-line" colspan=4>
    {.section github-pr}
      PR <a href="https://github.com/oilshell/oil/pull/{pr-number}">#{pr-number}</a>
      from <a href="https://github.com/oilshell/oil/tree/{head-ref}">{head-ref}</a>
      updated
    {.end}
    {.section commit-desc}
      <code>{@|html}</code>
    {.end}
  </td>

</tr>
<tr class="spacer">
  <td colspan=6><td/>
</tr>
''')


JOB_ROW_TEMPLATE = jsontemplate.Template('''\
<tr>
  <td>{job_num}</td>
  <td> <code><a href="{wwz_path}/">{job-name}</a></code> </td>
  <td><a href="{job_url}">{start_time_str}</a></td>
  <td>{pull_time_str}</td>
  <td>{run_time_str}</td>

  <td> <!-- status -->
  {.section passed}
    <span class="pass">pass</span>
  {.end}

  {.section failed}
    <span class="fail">FAIL</span><br/>
    <span class="fail-detail">
    {.section one-failure}
      task <code>{@}</code>
    {.end}

    {.section multiple-failures}
      {num-failures} of {num-tasks} tasks
    {.end}
    </span>
  {.end}

  </td>

  <!-- todo; spec details
  <td> </td>
  -->
</tr>
''')


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
      meta['passed'] = True
    else:
      failed = {}
      if num_failures == 1:
        failed['one-failure'] = failed_tasks[0]
      else:
        failed['multiple-failures'] = {
            'num-failures': num_failures,
            'num-tasks': num_tasks,
            }
      meta['failed'] = failed

    meta['run_time_str'] = _MinutesSeconds(total_elapsed)

    meta['pull_time_str'] = _ParsePullTime(meta.get('image-pull-time'))

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

    meta['git-branch'] = meta.get('GITHUB_REF')  or '?'

    # Show the branch ref/heads/soil-staging or ref/pull/1577/merge (linkified)
    pr_head_ref = meta.get('GITHUB_PR_HEAD_REF')
    pr_number = meta.get('GITHUB_PR_NUMBER')

    if pr_head_ref and pr_number:
      meta['github-pr'] = {
          'head-ref': pr_head_ref,
          'pr-number': pr_number,
          }

      # Show the user's commit, not the merge commit
      commit_hash = meta.get('GITHUB_PR_HEAD_SHA') or '?'

    else:
      # From soil/worker.sh save-metadata.  This is intended to be
      # CI-independent, while the environment variables above are from Github.
      meta['commit-desc'] = meta.get('commit-line', '?')
      commit_hash = meta.get('commit-hash') or '?'

    # TODO: Make a sourcehut link too
    meta['github-commit-link'] = {
        'commit-hash': commit_hash,
        'commit-hash-short': commit_hash[-8:],
        }

    # Metadata for "Job"

    meta['job-name'] = meta.get('job-name') or '?'

    # GITHUB_RUN_NUMBER (project-scoped) is shorter than GITHUB_RUN_ID (global
    # scope)
    meta['job_num'] = meta.get('JOB_ID') or meta.get('GITHUB_RUN_NUMBER') or '?'
    # For Github, we construct $JOB_URL in soil/github-actions.sh
    meta['job_url'] = meta.get('JOB_URL') or '?'

    prefix, _ = os.path.splitext(json_path)  # x/y/123/myjob
    last_two_parts = prefix.split('/')[-2:]  # ['123', 'myjob']
    rel_path = '/'.join(last_two_parts)  # 123/myjob

    meta['wwz_path'] = rel_path + '.wwz'  # 123/myjob.wwz

    yield meta


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
  return int(row.get('GITHUB_RUN_NUMBER', 0))


def HtmlHead(title):
  # Bust cache (e.g. Safari iPad seems to cache aggressively and doesn't
  # have Ctrl-F5)
  html_head.Write(sys.stdout, title,
      css_urls=['../web/base.css?cache=0', '../web/soil.css?cache=0'])


INDEX_TOP = jsontemplate.Template('''
  <body class="width50">
    <p id="home-link">
      <a href="/">travis-ci.oilshell.org</a>
      | <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>{title|html}</h1>

    <p style="text-align: right">
      <a href="raw.html">raw data</a>
    </p>

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
''')

INDEX_BOTTOM = '''\
    </table>

  </body>
</html>
'''


def IndexTop(title):
  d = {'title': title}
  print(INDEX_TOP.expand(d))


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
      print(RUN_ROW_TEMPLATE.expand(jobs[0]))

      for job in jobs:
        print(JOB_ROW_TEMPLATE.expand(job))

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
      print(RUN_ROW_TEMPLATE.expand(jobs[0]))

      for job in jobs:
        print(JOB_ROW_TEMPLATE.expand(job))

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

    # TODO: Github can be 
    # - $GITHUB_RUN_NUMBER/$job_name.json, and then sort by $GITHUB_RUN_NUMBER
    #   - this means that the 'raw-vm' task can look for 'cpp-small' directly
    # - sourcehut could be $JOB_ID/$job_name.json, and then sort by $JOB_ID
    #   - this is more flattened, but you can still do use list-json which does */*.json

    # Sort by 999 here
    # travis-ci.oilshell.org/github-jobs/999/foo.json

    prefixes.sort(key = lambda path: int(path.split('/')[-2]))

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
