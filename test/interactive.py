#!/usr/bin/env python3
"""
Test OSH in interactive mode.

Usage (run from project root):

    test/interactive.py

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
    if DEBUG:
      print(self.description)
    else:
      print(self.description, end='')

    #env = dict(os.environ)
    #env['PS1'] = 'test$ '
    env = None

    # Python 3: encoding required
    self.shell = pexpect.spawn(
        self.program, ['--rcfile', '/dev/null'], env=env, encoding='utf-8',
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


def main(argv):
  with InteractiveTest('wait builtin then SIGWINCH (issue 1067)') as osh:
    osh.sendline('sleep 1 &')
    osh.sendline('wait')

    time.sleep(0.1)

    # simulate window size change
    osh.kill(signal.SIGWINCH)

    osh.expect(r'.*\$')  # expect prompt

    osh.sendline('echo status=$?')
    osh.expect('status=0')

  #return

  with InteractiveTest('Ctrl-C during external command') as osh:
    osh.sendline('sleep 5')

    time.sleep(0.1)
    osh.sendintr()  # SIGINT

    osh.expect(r'.*\$')  # expect prompt

    osh.sendline('echo status=$?')
    osh.expect('status=130')

  with InteractiveTest('Ctrl-C during read builtin') as osh:
    osh.sendline('read')

    time.sleep(0.1)
    osh.sendintr()  # SIGINT

    osh.expect(r'.*\$')  # expect prompt

    osh.sendline('echo status=$?')
    osh.expect('status=130')

  with InteractiveTest('Ctrl-C during wait builtin') as osh:
    osh.sendline('sleep 5 &')
    osh.sendline('wait')

    time.sleep(0.1)
    osh.sendintr()  # SIGINT

    osh.expect(r'.*\$')  # expect prompt

    osh.sendline('echo status=$?')
    # TODO: Should be exit code 130 like bash
    osh.expect('status=0')

  with InteractiveTest('Ctrl-C during pipeline') as osh:
    osh.sendline('sleep 5 | cat')

    time.sleep(0.1)
    osh.sendintr()  # SIGINT

    osh.expect(r'.*\$')  # expect prompt

    osh.sendline('echo status=$?')
    osh.expect('status=130')

  with InteractiveTest("Ctrl-C during Command Sub (issue 467)") as osh:
    osh.sendline('`sleep 5`')

    time.sleep(0.1)
    osh.sendintr()  # SIGINT

    osh.expect(r'.*\$')  # expect prompt

    osh.sendline('echo status=$?')
    # TODO: This should be status 130 like bash
    osh.expect('status=0')

  with InteractiveTest("fg twice should not result in fatal error (issue 1004)") as osh:
    osh.expect(r'.*\$ ')
    osh.sendline("cat")
    stop_process__hack("cat")
    osh.expect("\r\n\\[PID \\d+\\] Stopped")
    osh.expect(r".*\$")
    osh.sendline("fg")
    osh.expect(r"Continue PID \d+")

    #osh.sendcontrol("c")
    osh.sendintr()  # SIGINT

    osh.expect(r".*\$")
    osh.sendline("fg")
    osh.expect("No job to put in the foreground")

  with InteractiveTest('Test resuming a killed process') as osh:
    osh.expect(r'.*\$ ')
    osh.sendline("cat")
    stop_process__hack("cat")
    osh.expect("\r\n\\[PID \\d+\\] Stopped")
    osh.expect(r".*\$")
    osh.sendline("fg")
    osh.expect(r"Continue PID \d+")
    send_signal("cat", signal.SIGINT)
    osh.expect(r".*\$")
    osh.sendline("fg")
    osh.expect("No job to put in the foreground")


  with InteractiveTest('Call fg after process exits (issue 721)') as osh:
    osh.expect(r".*\$")
    osh.sendline("cat")

    #osh.sendcontrol("c")
    osh.sendintr()  # SIGINT

    osh.expect(r".*\$")
    osh.sendline("fg")
    osh.expect("No job to put in the foreground")
    osh.expect(r".*\$")
    osh.sendline("fg")
    osh.expect("No job to put in the foreground")
    osh.expect(r".*\$")

  return 1 if g_failures else 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
