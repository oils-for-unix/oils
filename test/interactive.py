#!/usr/bin/env python3
"""
Test OSH in interactive mode.

To invoke this file, run the shell wrapper:

    test/interactive.sh all

Env Vars:
- OSH_TEST_INTERACTIVE_SHELL: override default shell path (default, bin/osh)
- OSH_TEST_INTERACTIVE_TIMEOUT: override default timeout (default, 2 seconds)

Exit Code:
- 0 if all tests pass
- 1 if any test fails.

Debug Mode:
- shows osh output
- halts on failure
"""
from __future__ import print_function

import os
import pexpect
import signal
import sys
import time

from core import ansi
from test import spec_lib  # Using this for a common interface

log = spec_lib.log


def get_pid_by_name(name):
  """Return the pid of the process matching `name`."""
  # XXX: make sure this is restricted to subprocesses under us.
  # This could be problematic on the continuous build if many tests are running
  # in parallel.
  output = pexpect.run('pgrep --exact --newest %s' % name)
  return int(output.split()[-1])


def send_signal(name, sig_num):
  """Kill the most recent process matching `name`."""
  os.kill(get_pid_by_name(name), sig_num)


# XXX: osh.sendcontrol("z") does not suspend the foreground process :(
#
# why does osh.sendcontrol("c") generate SIGINT, while osh.sendcontrol("z")
# appears to do nothing?
def stop_process__hack(name):
  """Send sigstop to the most recent process matching `name`"""
  send_signal(name, signal.SIGSTOP)


CASES = []

def register(skip_shells=None):
  if skip_shells is None:
    skip_shells = []

  def decorator(func):
    CASES.append((func.__doc__, func, skip_shells))
    return func
  return decorator

#
# Test Cases
#
# TODO:
# - Fold code from demo/
#   - sigwinch-bug.sh -- invokes $OSH with different snippets, then manual window resize
#   - signal-during-read.sh -- bash_read and osh_read with manual kill -HUP $PID
#     trap handler HUP
#   - bug-858-trap.sh -- wait and kill -USR1 $PID
#     trap handler USR1
#     trap handler USR2
# - Fill out this TEST MATRIX.
#
# A. Which shell?  osh, bash, dash, etc.
#
# B. What mode is it in?
#
#    1. Interactive (stdin is a terminal)
#    2. Non-interactive
#
# C. What is the main thread of the shell doing?
#
#    1. waiting for external process: sleep 1
#    2. wait builtin:                 sleep 5 & wait
#       variants: wait -n: this matters when testing exit code
#    3. read builtin                  read
#       variants: FIVE kinds, read -d, read -n, etc.
#    4. computation, e.g. fibonacci with $(( a + b ))
#
# if interactive:
#    5. keyboard input from terminal with select()
#
#    Another way to categorize the main loop:
#    1. running script code
#    2. running trap code
#    3. running TAB completion plugin code
#
# D. What is it interrupted by?
#
#    1. SIGINT
#    2. SIGTSTP
#    3. SIGWINCH
#    4. SIGUSR1 -- doesn't this quit?
#
# if interactive:
#    1. SIGINT  Ctrl-C from terminal (relies on signal distribution to child?)
#    2. SIGTSTP Ctrl-Z from terminal
#
# E. What is the signal state?
#
#    1. no trap handlers installed
#    2. trap 'echo X' SIGWINCH
#    3. trap 'echo X' SIGINT ?


@register()
def trapped_1(sh):
  'trapped SIGHUP during wait builtin'

  sh.sendline("trap 'echo HUP' HUP")
  sh.sendline('sleep 1 &')
  sh.sendline('wait')

  time.sleep(0.1)

  sh.kill(signal.SIGHUP)

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=129')


@register()
def trapped_sigint(sh):
  'trapped SIGINT during wait builtin'

  # This is different than Ctrl-C during wait builtin, because it's trapped!

  sh.sendline("trap 'echo INT' INT")
  sh.sendline('sleep 1 &')
  sh.sendline('wait')

  time.sleep(0.1)

  # simulate window size change
  sh.kill(signal.SIGINT)

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=130')


@register()
def sigwinch_trapped_wait(sh):
  'trapped SIGWINCH during wait builtin'

  sh.sendline("trap 'echo WINCH' WINCH")
  sh.sendline('sleep 1 &')
  sh.sendline('wait')

  time.sleep(0.1)

  # simulate window size change
  sh.kill(signal.SIGWINCH)

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=156')


@register()
def sigwinch_untrapped_wait(sh):
  'untrapped SIGWINCH during wait builtin (issue 1067)'

  sh.sendline('sleep 1 &')
  sh.sendline('wait')

  time.sleep(0.1)

  # simulate window size change
  sh.kill(signal.SIGWINCH)

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=0')


@register()
def t1(sh):
  'Ctrl-C during external command'

  sh.sendline('sleep 5')

  time.sleep(0.1)
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=130')


@register()
def t4(sh):
  'Ctrl-C during pipeline'
  sh.sendline('sleep 5 | cat')

  time.sleep(0.1)
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=130')


@register()
def t2(sh):
  'Ctrl-C during read builtin'

  sh.sendline('read myvar')

  time.sleep(0.1)
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=130')


@register()
def c_wait(sh):
  'Ctrl-C (untrapped) during wait builtin'

  sh.sendline('sleep 5 &')
  sh.sendline('wait')

  time.sleep(0.1)

  # TODO: actually send Ctrl-C through the terminal, not SIGINT?
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=130')


@register()
def c_wait_n(sh):
  'Ctrl-C (untrapped) during wait -n builtin'

  sh.sendline('sleep 5 &')
  sh.sendline('wait -n')

  time.sleep(0.1)

  # TODO: actually send Ctrl-C through the terminal, not SIGINT?
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=130')


@register()
def t5(sh):
  'Ctrl-C during Command Sub (issue 467)'
  sh.sendline('`sleep 5`')

  time.sleep(0.1)
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  # TODO: This should be status 130 like bash
  sh.expect('status=130')


@register(skip_shells=['bash'])
def t6(sh):
  'fg twice should not result in fatal error (issue 1004)'
  sh.expect(r'.*\$ ')
  sh.sendline("cat")
  stop_process__hack("cat")
  sh.expect("\r\n\\[PID \\d+\\] Stopped")
  sh.expect(r".*\$")
  sh.sendline("fg")
  sh.expect(r"Continue PID \d+")

  #sh.sendcontrol("c")
  sh.sendintr()  # SIGINT

  sh.expect(r".*\$")
  sh.sendline("fg")
  sh.expect("No job to put in the foreground")


@register(skip_shells=['bash'])
def t7(sh):
  'Test resuming a killed process'
  sh.expect(r'.*\$ ')
  sh.sendline("cat")
  stop_process__hack("cat")
  sh.expect("\r\n\\[PID \\d+\\] Stopped")
  sh.expect(r".*\$")
  sh.sendline("fg")
  sh.expect(r"Continue PID \d+")
  send_signal("cat", signal.SIGINT)
  sh.expect(r".*\$")
  sh.sendline("fg")
  sh.expect("No job to put in the foreground")


@register(skip_shells=['bash'])
def t8(sh):
  'Call fg after process exits (issue 721)'

  sh.expect(r".*\$")
  sh.sendline("cat")

  #osh.sendcontrol("c")
  sh.sendintr()  # SIGINT

  sh.expect(r".*\$")
  sh.sendline("fg")
  sh.expect("No job to put in the foreground")
  sh.expect(r".*\$")
  sh.sendline("fg")
  sh.expect("No job to put in the foreground")
  sh.expect(r".*\$")


@register()
def t9(sh):
  'syntax error makes status=2'

  sh.sendline('syntax ) error')

  #time.sleep(0.1)

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=2')  # osh, bash, dash

  # mksh gives status=1, and zsh doesn't give anything?


class AnsiOutput(object):

  def __init__(self, f):
    self.f = f

  def WriteHeader(self, sh_labels):
    self.f.write(ansi.BOLD)
    self.f.write('case\t')  # case number
    for sh_label in sh_labels:
      self.f.write(sh_label)
      self.f.write('\t')
    self.f.write(ansi.RESET)
    self.f.write('\n')


class Result(object):
  SKIP = 1
  OK = 2
  FAIL = 3


def RunCases(cases, case_predicate, shell_pairs, results):
  for i, (desc, func, skip_shells) in enumerate(cases):
    if not case_predicate(i, desc):
      continue

    result_row = [i]

    for shell_label, shell_path in shell_pairs:
      skip = shell_label in skip_shells
      skip_str = 'SKIP' if skip else ''

      print()
      print('%s\t%d\t%s\t%s' % (skip_str, i, shell_label, desc))
      print()

      if skip:
        result_row.append(Result.SKIP)
        continue

      env = None

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
          shell_path, sh_argv, env=env, encoding='utf-8', timeout=1.0)

      # Generally don't want local echo, it gets confusing fast.
      sh.setecho(False)

      ok = True
      try:
        func(sh)
      except Exception as e:
        import traceback
        print(e)
        result_row.append(Result.FAIL)
        ok = False

      finally:
        sh.close()

      if ok:
        result_row.append(Result.OK)

    result_row.append(desc)
    results.append(result_row) 


def PrintResults(shell_pairs, results):
  f = sys.stdout

  if f.isatty():
    fail_color = ansi.BOLD + ansi.RED
    ok_color = ansi.BOLD + ansi.GREEN
    reset = ansi.RESET
  else:
    fail_color = ''
    ok_color = ''
    reset = ''

  f.write('\n')

  # TODO: Might want an HTML version too
  out_f = AnsiOutput(f)
  out_f.WriteHeader([shell_label for shell_label, _ in shell_pairs])

  num_failures = 0

  for row in results:

    case_num = row[0]
    desc = row[-1]

    f.write('%d\t' % case_num)

    for cell in row[1:-1]:
      if cell == Result.SKIP:
        f.write('SKIP\t')
      elif cell == Result.FAIL:
        num_failures += 1
        f.write('%sFAIL%s\t' % (fail_color, reset))
      elif cell == Result.OK:
        f.write('%sok%s\t' % (ok_color, reset))
      else:
        raise AssertionError(cell)

    f.write(desc)
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

  results = []  # each row is a list

  RunCases(CASES, case_predicate, shell_pairs, results)

  num_failures = PrintResults(shell_pairs, results)

  if opts.osh_failures_allowed != num_failures:
    log('test/interactive: Expected %d failures, got %d', opts.osh_failures_allowed, num_failures)
    return 1

  return 0



if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
