#!/usr/bin/env python3
"""
State Machine style tests with pexpect, e.g. for interactive mode.

To invoke this file, run the shell wrapper:

    test/stateful.sh all
"""
from __future__ import print_function

import os
import pexpect
import signal
import sys

from core import ansi
from test import spec_lib  # Using this for a common interface

log = spec_lib.log


def expect_prompt(sh):
  sh.expect(r'.*\$')


def get_pid_by_name(name):
  """Return the pid of the process matching `name`."""
  # XXX: make sure this is restricted to subprocesses under us.
  # This could be problematic on the continuous build if many tests are running
  # in parallel.
  output = pexpect.run('pgrep --exact --newest %s' % name)
  #log('pgrep output %r' % output)
  return int(output.split()[-1])


def send_signal(name, sig_num):
  """Kill the most recent process matching `name`."""
  os.kill(get_pid_by_name(name), sig_num)


def stop_process__hack(name):
  """Send sigstop to the most recent process matching `name`

  Hack in place of sh.sendcontrol('z'), which sends SIGTSTP.  Why doesn't OSH
  respond to this, or why don't the child processes respond?

  TODO: Fix OSH and get rid of this hack.
  """
  send_signal(name, signal.SIGSTOP)


# Mutated by each test file.
CASES = []

def register(skip_shells=None):
  if skip_shells is None:
    skip_shells = []

  def decorator(func):
    CASES.append((func.__doc__, func, skip_shells))
    return func
  return decorator


class Result(object):
  SKIP = 1
  OK = 2
  FAIL = 3


class TestRunner(object):

  def __init__(self, num_retries, pexpect_timeout):
    self.num_retries = num_retries
    self.pexpect_timeout = pexpect_timeout

  def RunOnce(self, shell_path, shell_label, func):
    sh_argv = []
    if shell_label in ('bash', 'osh'):
      sh_argv.extend(['--rcfile', '/dev/null'])
    # Why the heck is --norc different from --rcfile /dev/null in bash???  This
    # makes it so the prompt of the parent shell doesn't leak.  Very annoying.
    if shell_label == 'bash':
      sh_argv.append('--norc')
    #print(sh_argv)

    # Python 3: encoding required
    sh = pexpect.spawn(
        shell_path, sh_argv, encoding='utf-8', timeout=self.pexpect_timeout)

    sh.shell_label = shell_label  # for tests to use

    # Generally don't want local echo, it gets confusing fast.
    sh.setecho(False)

    ok = True
    try:
      func(sh)
    except Exception as e:
      import traceback
      traceback.print_exc(file=sys.stderr)
      return Result.FAIL
      ok = False

    finally:
      sh.close()

    if ok:
      return Result.OK

  def RunCase(self, shell_path, shell_label, func):
    result = self.RunOnce(shell_path, shell_label, func)

    if result == Result.OK:
      return result, -1  # short circuit for speed

    elif result == Result.FAIL:
      num_success = 0
      if self.num_retries:
        log('\tFAILED first time: Retrying 4 times')
        for i in range(self.num_retries):
          log('\tRetry %d of %d', i+1, self.num_retries)
          result = self.RunOnce(shell_path, shell_label, func)
          if result == Result.OK:
            num_success += 1
      else:
        log('\tFAILED')

      if num_success >= 2:
        return Result.OK, num_success
      else:
        return Result.FAIL, num_success

    else:
      raise AssertionError(result)

  def RunCases(self, cases, case_predicate, shell_pairs, result_table, flaky):
    for case_num, (desc, func, skip_shells) in enumerate(cases):
      if not case_predicate(case_num, desc):
        continue

      result_row = [case_num]

      for shell_label, shell_path in shell_pairs:
        skip = shell_label in skip_shells
        skip_str = 'SKIP' if skip else ''

        print()
        print('%s\t%d\t%s\t%s' % (skip_str, case_num, shell_label, desc))
        print()
        sys.stdout.flush()  # prevent interleaving

        if skip:
          result_row.append(Result.SKIP)
          flaky[case_num, shell_label] = -1
          continue

        result, retries = self.RunCase(shell_path, shell_label, func)
        flaky[case_num, shell_label] = retries

        result_row.append(result)

      result_row.append(desc)
      result_table.append(result_row) 


def PrintResults(shell_pairs, result_table, flaky, num_retries, f):

  # Note: In retrospect, it would be better if every process writes a "long"
  # TSV file of results.
  # And then we concatenate them and write the "wide" summary here.

  if f.isatty():
    fail_color = ansi.BOLD + ansi.RED
    ok_color = ansi.BOLD + ansi.GREEN
    bold = ansi.BOLD
    reset = ansi.RESET
  else:
    fail_color = ''
    ok_color = ''
    bold = ''
    reset = ''

  f.write('\n')

  # TODO: Might want an HTML version too
  sh_labels = [shell_label for shell_label, _ in shell_pairs]

  f.write(bold)
  f.write('case\t')  # case number
  for sh_label in sh_labels:
    f.write(sh_label)
    f.write('\t')
  f.write(reset)
  f.write('\n')

  num_failures = 0

  for row in result_table:

    case_num = row[0]
    desc = row[-1]

    f.write('%d\t' % case_num)

    num_shells = len(row) - 2 
    extra_row = [''] * num_shells

    for j, cell in enumerate(row[1:-1]):
      shell_label = sh_labels[j]

      num_success = flaky[case_num, shell_label]
      if num_success != -1:
        # the first of 5 failed
        extra_row[j] = '%d/%d ok' % (num_success, num_retries+1)

      if cell == Result.SKIP:
        f.write('SKIP\t')
      elif cell == Result.FAIL:
        num_failures += 1
        f.write('%sFAIL%s\t' % (fail_color, reset ))
      elif cell == Result.OK:
        f.write('%sok%s\t' % (ok_color, reset))
      else:
        raise AssertionError(cell)

    f.write(desc)
    f.write('\n')

    if any(extra_row):
      for cell in extra_row:
        f.write('\t%s' % cell)
      f.write('\n')

  return num_failures


def main(argv):
  # NOTE: Some options are ignored
  o = spec_lib.Options()
  opts, argv = o.parse_args(argv)

  # List test cases and return
  if opts.do_list:
    for i, (desc, _, _) in enumerate(CASES):
      print('%d\t%s' % (i, desc))
    return

  shells = argv[1:]
  if not shells:
    raise RuntimeError('Expected shells to run')

  shell_pairs = spec_lib.MakeShellPairs(shells)

  if opts.range:
    begin, end = spec_lib.ParseRange(opts.range)
    case_predicate = spec_lib.RangePredicate(begin, end)
  elif opts.regex:
    desc_re = re.compile(opts.regex, re.IGNORECASE)
    case_predicate = spec_lib.RegexPredicate(desc_re)
  else:
    case_predicate = lambda i, case: True

  if 0:
    print(shell_pairs)
    print(CASES)

  result_table = []  # each row is a list
  flaky = {}  # (case_num, shell) -> (succeeded, attempted)

  r = TestRunner(opts.num_retries, opts.pexpect_timeout)
  r.RunCases(CASES, case_predicate, shell_pairs, result_table, flaky)

  if opts.results_file:
    results_f = open(opts.results_file, 'w')
  else:
    results_f = sys.stdout
  num_failures = PrintResults(shell_pairs, result_table, flaky, opts.num_retries, results_f)

  results_f.close()

  if opts.osh_failures_allowed != num_failures:
    log('%s: Expected %d failures, got %d', sys.argv[0], opts.osh_failures_allowed, num_failures)
    return 1

  return 0



if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
