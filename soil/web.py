#!/usr/bin/env python2
"""
soil/web.py - Dashboard that uses the "Event Sourcing" Paradigm

Given state like this:

https://test.oils-for-unix.org/
  github-jobs/
    1234/  # $GITHUB_RUN_NUMBER
      cpp-small.tsv    # benchmarks/time.py output.  Success/failure for each task.
      cpp-small.json   # metadata when job is DONE

      (cpp-small.wwz is linked to, but not part of the state.)

      (cpp-small.state  # maybe for more transient events)

This script generates:

https://test.oils-for-unix.org/
  github-jobs/
    tmp-$$.index.html  # jobs for all runs
    1234/
      tmp-$$.index.html  # jobs and tasks for a given run
      tmp-$$.remove.txt  # TODO: consolidate 'cleanup', to make it faster

    # For sourcehut
    git-0101abab/
      tmp-$$.index.html

How to test changes to this file:

  $ soil/web-init.sh deploy-code
  $ soil/web-worker.sh remote-rewrite-jobs-index github- ${GITHUB_RUN_NUMBER}
  $ soil/web-worker.sh remote-rewrite-jobs-index sourcehut- git-${commit_hash}

"""
from __future__ import print_function

import collections
import csv
import datetime
import json
import itertools
import os
import re
import sys
from doctools import html_head
from vendor import jsontemplate


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def PrettyTime(now, start_time):
  """
  Return a pretty string like 'an hour ago', 'Yesterday', '3 months ago', 'just
  now', etc
  """
  # *** UNUSED because it only makes sense on a dynamic web page! ***
  # Loosely based on
  # https://stackoverflow.com/questions/1551382/user-friendly-time-format-in-python

  return 'unused'


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
  for line in time_p_str.splitlines():
    m = LINE_RE.match(line)
    if m:
      name, value = m.groups()
      if name == 'real':
        return _MinutesSeconds(float(value))

  return '-'  # Not found


DETAILS_RUN_T = jsontemplate.Template('''\

<table>
<tr class="spacer">
  <td></td>
</tr>

<tr class="commit-row">
  <td>
    <code>
      {.section github-commit-link}
      <a href="https://github.com/oilshell/oil/commit/{commit-hash}">{commit-hash-short}</a>
      {.end}

      {.section sourcehut-commit-link}
      <a href="https://git.sr.ht/~andyc/oil/commit/{commit-hash}">{commit-hash-short}</a>
      {.end}
    </code>
  </td>

  <td class="commit-line">
    {.section github-pr}
      <i>
      PR <a href="https://github.com/oilshell/oil/pull/{pr-number}">#{pr-number}</a>
      from <a href="https://github.com/oilshell/oil/tree/{head-ref}">{head-ref}</a>
      </i>
    {.end}
    {.section commit-desc}
      {@|html}
    {.end}

    {.section git-branch}
      <br/>
      <div style="text-align: right; font-family: monospace">{@}</div>
    {.end}
  </td>

</tr>
<tr class="spacer">
  <td><td/>
</tr>

</table>
''')


DETAILS_TABLE_T = jsontemplate.Template('''\
<table class="col1-right col3-right col4-right col5-right col6-right">

  <thead>
    <tr>
      <td>ID</td>
      <td>Job Name</td>
      <td>Start Time</td>
      <td>Pull Time</td>
      <td>Run Time</td>
      <td>Status</td>
    </tr>
  </thead>

  {.repeated section jobs}
    <tr>

      <td>{job_num}</td>

      <!-- internal link -->
      <td> <code><a href="#job-{job-name}">{job-name}</a></code> </td>

      <td><a href="{job_url}">{start_time_str}</a></td>
      <td>
        {.section pull_time_str}
          <a href="{run_wwz_path}/_tmp/soil/image.html">{@}</a>
        {.or}
          -
        {.end}
      </td>

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

    </tr>
  {.end}

</table>
''')


def ParseJobs(stdin):
  """
  Given the output of list-json, open JSON and corresponding TSV, and yield a
  list of JSON template rows.
  """
  for i, line in enumerate(stdin):
    json_path = line.strip()

    #if i % 20 == 0:
    #  log('job %d = %s', i, json_path)

    with open(json_path) as f:
      meta = json.load(f)
    #print(meta)

    tsv_path = json_path[:-5] + '.tsv'
    #log('%s', tsv_path)

    all_tasks = []
    failed_tasks = []
    total_elapsed = 0.0

    with open(tsv_path) as f:
      reader = csv.reader(f, delimiter='\t')

      try:
        for row in reader:
          t = {}
          # Unpack, matching _tmp/soil/INDEX.tsv
          ( status, elapsed,
            t['name'], t['script_name'], t['func'], results_url) = row

          t['results_url'] = None if results_url == '-' else results_url

          status = int(status)
          elapsed = float(elapsed)

          t['elapsed_str'] = _MinutesSeconds(elapsed)

          all_tasks.append(t)

          t['status'] = status
          if status == 0:
            t['passed'] = True
          else:
            t['failed'] = True
            failed_tasks.append(t)

          total_elapsed += elapsed

      except (IndexError, ValueError) as e:
        raise RuntimeError('Error in %r: %s (%r)' % (tsv_path, e, row))

    # So we can print task tables
    meta['tasks'] = all_tasks

    num_failures = len(failed_tasks)

    if num_failures == 0:
      meta['passed'] = True
    else:
      failed = {}
      if num_failures == 1:
        failed['one-failure'] = failed_tasks[0]['name']
      else:
        failed['multiple-failures'] = {
            'num-failures': num_failures,
            'num-tasks': len(all_tasks),
            }
      meta['failed'] = failed

    meta['run_time_str'] = _MinutesSeconds(total_elapsed)

    pull_time = meta.get('image-pull-time')
    if pull_time is not None:
      meta['pull_time_str'] = _ParsePullTime(pull_time)

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

    # Metadata for a "run".  A run is for a single commit, and consists of many
    # jobs.

    meta['git-branch'] = meta.get('GITHUB_REF')

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

    commit_link = {
        'commit-hash': commit_hash,
        'commit-hash-short': commit_hash[:8],
        }

    meta['job-name'] = meta.get('job-name') or '?'

    # Metadata for "Job"

    # GITHUB_RUN_NUMBER (project-scoped) is shorter than GITHUB_RUN_ID (global
    # scope)
    github_run = meta.get('GITHUB_RUN_NUMBER')

    if github_run:
      meta['job_num'] = github_run
      meta['index_run_url'] = '%s/' % github_run

      meta['github-commit-link'] = commit_link

      run_url_prefix = ''
    else:
      sourcehut_job_id = meta['JOB_ID'] 
      meta['job_num'] = sourcehut_job_id
      meta['index_run_url'] = 'git-%s/' % meta['commit-hash']

      meta['sourcehut-commit-link'] = commit_link

      # sourcehut doesn't have RUN ID, so we're in
      # sourcehut-jobs/git-ab01cd/index.html, and need to find sourcehut-jobs/123/foo.wwz
      run_url_prefix = '../%s/' % sourcehut_job_id

    # For Github, we construct $JOB_URL in soil/github-actions.sh
    meta['job_url'] = meta.get('JOB_URL') or '?'

    prefix, _ = os.path.splitext(json_path)  # x/y/123/myjob
    parts = prefix.split('/')

    # Paths relative to github-jobs/1234/
    meta['run_wwz_path'] = run_url_prefix + parts[-1] + '.wwz'  # myjob.wwz
    meta['run_tsv_path'] = run_url_prefix + parts[-1] + '.tsv'  # myjob.tsv
    meta['run_json_path'] = run_url_prefix + parts[-1] + '.json'  # myjob.json

    # Relative to github-jobs/
    last_two_parts = parts[-2:]  # ['123', 'myjob']
    meta['index_wwz_path'] = '/'.join(last_two_parts) + '.wwz'  # 123/myjob.wwz

    yield meta


HTML_BODY_TOP_T = jsontemplate.Template('''
  <body class="width50">
    <p id="home-link">
        <a href="..">Up</a>
      | <a href="/">Home</a>
      | <a href="//oilshell.org/">oilshell.org</a>
    </p>

    <h1>{title|html}</h1>
''')

HTML_BODY_BOTTOM = '''\
  </body>
</html>
'''

INDEX_HEADER = '''\
<table>
  <thead>
    <tr>
      <td colspan=1> Commit </td>
      <td colspan=1> Description </td>
    </tr>
  </thead>
'''

INDEX_RUN_ROW_T = jsontemplate.Template('''\
<tr class="spacer">
  <td colspan=2></td>
</tr>

<tr class="commit-row">
  <td>
    <code>
      {.section github-commit-link}
      <a href="https://github.com/oilshell/oil/commit/{commit-hash}">{commit-hash-short}</a>
      {.end}

      {.section sourcehut-commit-link}
      <a href="https://git.sr.ht/~andyc/oil/commit/{commit-hash}">{commit-hash-short}</a>
      {.end}
    </code>

    </td>
  </td>

  <td class="commit-line">
    {.section github-pr}
      <i>
      PR <a href="https://github.com/oilshell/oil/pull/{pr-number}">#{pr-number}</a>
      from <a href="https://github.com/oilshell/oil/tree/{head-ref}">{head-ref}</a>
      </i>
    {.end}
    {.section commit-desc}
      {@|html}
    {.end}

    {.section git-branch}
      <br/>
      <div style="text-align: right; font-family: monospace">{@}</div>
    {.end}
  </td>

</tr>
<tr class="spacer">
  <td colspan=2><td/>
</tr>
''')

INDEX_JOBS_T = jsontemplate.Template('''\
<tr>
  <td>
  </td>
  <td>
    <a href="{index_run_url}">All Jobs and Tasks</a>
  </td>
</tr>

{.section jobs-passed}
  <tr>
    <td class="pass">
      Passed
    </td>
    <td>
      {.repeated section @}
        <code class="pass">{job-name}</code>
        <!--
        <span class="pass"> &#x2713; </span>
        -->
      {.alternates with}
        &nbsp; &nbsp;
      {.end}
    </td>
  </tr>
{.end}

{.section jobs-failed}
  <tr>
    <td class="fail">
      Failed
    </td>
    <td>
      {.repeated section @}
        <span class="fail"> &#x2717; </span>
        <code><a href="{index_run_url}#job-{job-name}">{job-name}</a></code>

        <span class="fail-detail">
        {.section failed}
          {.section one-failure}
            - task <code>{@}</code>
          {.end}

          {.section multiple-failures}
            - {num-failures} of {num-tasks} tasks
          {.end}
        {.end}
        </span>

      {.alternates with}
        <br />
      {.end}
    </td>
  </tr>
{.end}

<tr class="spacer">
  <td colspan=3> &nbsp; </td>
</tr>

''')

def PrintIndexHtml(title, groups, f=sys.stdout):
  # Bust cache (e.g. Safari iPad seems to cache aggressively and doesn't
  # have Ctrl-F5)
  html_head.Write(f, title,
      css_urls=['../web/base.css?cache=0', '../web/soil.css?cache=0'])

  d = {'title': title}
  print(HTML_BODY_TOP_T.expand(d), file=f)

  print(INDEX_HEADER, file=f)

  for key, jobs in groups.iteritems():
    # All jobs have run-level metadata, so just use the first

    print(INDEX_RUN_ROW_T.expand(jobs[0]), file=f)

    summary = {
        'jobs-passed': [],
        'jobs-failed': [],
        'index_run_url': jobs[0]['index_run_url'],
        }

    for job in jobs:
      if job.get('passed'):
        summary['jobs-passed'].append(job)
      else:
        summary['jobs-failed'].append(job)

    print(INDEX_JOBS_T.expand(summary), file=f)

  print(' </table>', file=f)
  print(HTML_BODY_BOTTOM, file=f)


TASK_TABLE_T = jsontemplate.Template('''\

<h2>All Tasks</h2>

<!-- right justify elapsed and status -->
<table class="col2-right col3-right col4-right">

{.repeated section jobs}

<tr> <!-- link here -->
  <td colspan=4>
    <a name="job-{job-name}"></a>
  </td>
</tr>

<tr style="background-color: #EEE">
  <td colspan=3>
    <b>{job-name}</b>
    &nbsp;
    &nbsp;
    &nbsp;
    <a href="{run_wwz_path}/">wwz</a>
    &nbsp;
    <a href="{run_tsv_path}">TSV</a>
    &nbsp;
    <a href="{run_json_path}">JSON</a>
  <td>
    <a href="">Up</a>
  </td>
</tr>

<tr class="spacer">
  <td colspan=4> &nbsp; </td>
</tr>

<tr style="font-weight: bold">
  <td>Task</td>
  <td>Results</td>
  <td>Elapsed</td>
  <td>Status</td>
</tr>

  {.repeated section tasks}
  <tr>
    <td>
      <a href="{run_wwz_path}/_tmp/soil/logs/{name}.txt">{name}</a> <br/>
       <code>{script_name} {func}</code>
    </td>

    <td>
      {.section results_url}
      <a href="{run_wwz_path}/{@}">Results</a>
      {.or}
      {.end}
    </td>

    <td>{elapsed_str}</td>

    {.section passed}
      <td>{status}</td>
    {.end}
    {.section failed}
      <td class="fail">status: {status}</td>
    {.end}

  </tr>
  {.end}

<tr class="spacer">
  <td colspan=4> &nbsp; </td>
</tr>

{.end}

</table>

''')


def PrintRunHtml(title, jobs, f=sys.stdout):
  """Print index for jobs in a single run."""

  # Have to descend an extra level
  html_head.Write(f, title,
      css_urls=['../../web/base.css?cache=0', '../../web/soil.css?cache=0'])

  d = {'title': title}
  print(HTML_BODY_TOP_T.expand(d), file=f)

  print(DETAILS_RUN_T.expand(jobs[0]), file=f)

  d2 = {'jobs': jobs}
  print(DETAILS_TABLE_T.expand(d2), file=f)

  print(TASK_TABLE_T.expand(d2), file=f)

  print(HTML_BODY_BOTTOM, file=f)


def GroupJobs(jobs, key_func):
  """
  Expands groupby result into a simple dict
  """
  groups = itertools.groupby(jobs, key=key_func)

  d = collections.OrderedDict()

  for key, job_iter in groups:
    jobs = list(job_iter)

    jobs.sort(key=ByTaskRunStartTime, reverse=True)

    d[key] = jobs

  return d


def ByTaskRunStartTime(row):
  return int(row.get('task-run-start-time', 0))

def ByCommitDate(row):
  # Written in the shell script
  # This is in ISO 8601 format (git log %aI), so we can sort by it.
  return row.get('commit-date', '?')

def ByCommitHash(row):
  return row.get('commit-hash', '?')

def ByGithubRun(row):
  # Written in the shell script
  # This is in ISO 8601 format (git log %aI), so we can sort by it.
  return int(row.get('GITHUB_RUN_NUMBER', 0))


def main(argv):
  action = argv[1]

  if action == 'sourcehut-index':
    index_out = argv[2]
    run_index_out = argv[3]
    run_id = argv[4]  # looks like git-0101abab

    assert run_id.startswith('git-'), run_id
    commit_hash = run_id[4:]

    jobs = list(ParseJobs(sys.stdin))

    # sourcehut doesn't have a build number.
    # - Sort by descnding commit date.  (Minor problem: Committing on a VM with
    #   bad clock can cause commits "in the past")
    # - Group by commit HASH, because 'git rebase' can crate different commits
    #   with the same date.
    jobs.sort(key=ByCommitDate, reverse=True)
    groups = GroupJobs(jobs, ByCommitHash)

    title = 'Recent Jobs (sourcehut)'
    with open(index_out, 'w') as f:
      PrintIndexHtml(title, groups, f=f)

    jobs = groups[commit_hash]
    title = 'Jobs for commit %s' % commit_hash
    with open(run_index_out, 'w') as f:
      PrintRunHtml(title, jobs, f=f)

  elif action == 'github-index':

    index_out = argv[2]
    run_index_out = argv[3]
    run_id = int(argv[4])  # compared as an integer

    jobs = list(ParseJobs(sys.stdin))

    jobs.sort(key=ByGithubRun, reverse=True)  # ordered
    groups = GroupJobs(jobs, ByGithubRun)

    title = 'Recent Jobs (Github Actions)'
    with open(index_out, 'w') as f:
      PrintIndexHtml(title, groups, f=f)

    jobs = groups[run_id]
    title = 'Jobs for run %d' % run_id

    with open(run_index_out, 'w') as f:
      PrintRunHtml(title, jobs, f=f)

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

    # TODO: clean up git-$hash dirs
    #
    # github-jobs/
    #   $GITHUB_RUN_NUMBER/
    #     cpp-tarball.{json,wwz,tsv}
    #     dummy.{json,wwz,tsv}
    #   git-$hash/
    #     oils-for-unix.tar
    #
    # sourcehut-jobs/
    #   1234/
    #     cpp-tarball.{json,wwz,tsv}
    #   1235/
    #     dummy.{json,wwz,tsv}
    #   git-$hash/
    #     index.html  # HTML for this job
    #     oils-for-unix.tar
    #
    # We might have to read the most recent JSON, find the corresponding $hash,
    # and print that dir.
    #
    # Another option is to use a real database, rather than the file system!

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
