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


SHELL = os.environ.get("OSH_TEST_INTERACTIVE_SHELL", "bin/osh")
TIMEOUT = int(os.environ.get("OSH_TEST_INTERACTIVE_TIMEOUT", 3))
DEBUG = True
#DEBUG = False

# keep track of failures so we can report exit status
global g_failures
g_failures = 0


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


class InteractiveTest(object):
  """Define a test case for the interactive shell.

  This is implemented as a context-manager wrapper around
  pexpect.spawn, use like this:

  with InteractiveTest("Describe the test") as osh:
     osh.sendline(...)
     osh.expect(...)
     ...
  """

  def __init__(self, description, program=SHELL):
    self.program = program
    self.shell = None
    self.description = description

  def __enter__(self):
    if 0:
      if DEBUG:
        print(self.description)
      else:
        print(self.description, end='')

    #env = dict(os.environ)
    #env['PS1'] = 'test$ '
    env = None

    sh_argv = ['--rcfile', '/dev/null']

    # Why the heck is --norc different from --rcfile /dev/null in bash???  This
    # makes it so the prompt of the parent shell doesn't leak.  Very annoying.
    if self.program == 'bash':
      sh_argv.append('--norc')
    #print(sh_argv)

    # Python 3: encoding required
    self.shell = pexpect.spawn(
        self.program, sh_argv, env=env, encoding='utf-8',
        timeout=TIMEOUT)

    # suppress output when DEBUG is not set.
    if DEBUG:
      self.shell.logfile = sys.stdout

    # generally don't want local echo, it gets confusing fast.
    self.shell.setecho(False)
    return self.shell

  def __exit__(self, t, v, tb):
    global g_failures
    self.shell.close()

    if not DEBUG:
      # show result of test
      if tb:
        g_failures += 1
        print("... Fail")
      else:
        print("... OK")
      # Allow other tests to keep running
      return True
    else:
      # Fail fast when in debug mode.
      pass



CASES = []

def register(skip_shells=None):
  if skip_shells is None:
    skip_shells = []

  def decorator(func):
    CASES.append((func.__doc__, func, skip_shells))
    return func
  return decorator


# TODO: Make this pass in OSH
@register(skip_shells=['osh'])
def a(sh):
  'wait builtin then SIGWINCH (issue 1067)'

  sh.sendline('sleep 1 &')
  sh.sendline('wait')

  time.sleep(0.1)

  # simulate window size change
  sh.kill(signal.SIGWINCH)

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=0')


@register()
def b(sh):
  'Ctrl-C during external command'

  sh.sendline('sleep 5')

  time.sleep(0.1)
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=130')


@register()
def c(sh):
  'Ctrl-C during read builtin'

  sh.sendline('read')

  time.sleep(0.1)
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=130')


# TODO: fix on OSH
@register(skip_shells=['osh'])
def d(sh):
  'Ctrl-C during wait builtin'

  sh.sendline('sleep 5 &')
  sh.sendline('wait')

  time.sleep(0.1)
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  # TODO: Should be exit code 130 like bash
  sh.expect('status=130')


@register()
def e(sh):
  'Ctrl-C during pipeline'
  sh.sendline('sleep 5 | cat')

  time.sleep(0.1)
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=130')


# TODO: make it work on OSH
@register(skip_shells=['osh'])
def f(sh):
  'Ctrl-C during Command Sub (issue 467)'
  sh.sendline('`sleep 5`')

  time.sleep(0.1)
  sh.sendintr()  # SIGINT

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  # TODO: This should be status 130 like bash
  sh.expect('status=130')


@register(skip_shells=['bash'])
def g(sh):
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
def h(sh):
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
def j(sh):
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

      with InteractiveTest(desc, program=shell_path) as sh:
        func(sh)

      # TODO: Failing will raise an exception and we won't print anything?
      result_row.append(Result.OK)

    result_row.append(desc)
    results.append(result_row) 


def PrintResults(shell_pairs, results):
  f = sys.stderr

  f.write('\n')

  # TODO: Might want an HTML version too
  out_f = AnsiOutput(f)
  out_f.WriteHeader([shell_label for shell_label, _ in shell_pairs])

  for row in results:

    case_num = row[0]
    desc = row[-1]

    f.write('%d\t' % case_num)

    for cell in row[1:-1]:
      if cell == Result.SKIP:
        f.write('SKIP\t')
      elif cell == Result.OK:
        f.write('%sok%s\t' % (ansi.BOLD + ansi.GREEN, ansi.RESET))
      else:
        raise AssertionError(cell)

    f.write(desc)
    f.write('\n')


def main(argv):
  # NOTE: Some options are ignored
  o = spec_lib.Options()
  opts, argv = o.parse_args(argv)

  shells = argv[1:]
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

  results = []  # type: List[Dict[shell_label, result]]

  RunCases(CASES, case_predicate, shell_pairs, results)

  PrintResults(shell_pairs, results)

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
