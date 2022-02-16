#!/usr/bin/env python3
"""
spec/stateful/job_control.py
"""
from __future__ import print_function

import signal
import sys
import time

import harness
from harness import register, stop_process__hack, expect_prompt
from test.spec_lib import log


# Hint from Stevens book
#
# http://lkml.iu.edu/hypermail/linux/kernel/1006.2/02460.html
# "TIOCSIG Generate a signal to processes in the
# current process group of the pty."

# Generated from C header file
TIOCSIG = 0x40045436


def ctrl_c(sh):
  sh.sendcontrol('c')
  #fcntl.ioctl(sh.child_fd, TIOCSIG, signal.SIGINT)


def ctrl_z(sh):
  sh.sendcontrol('z')
  #fcntl.ioctl(sh.child_fd, TIOCSIG, signal.SIGTSTP)


def expect_no_job(sh):
  """Helper function."""
  if sh.shell_label == 'osh':
    sh.expect('No job to put in the foreground')
  elif sh.shell_label == 'dash':
    sh.expect('.*fg: No current job')
  elif sh.shell_label == 'bash':
    sh.expect('.*fg: current: no such job.*')
  else:
    raise AssertionError()


@register()
def bug_1004(sh):
  'fg twice should not result in fatal error (issue 1004)'

  expect_prompt(sh)
  sh.sendline('cat')

  time.sleep(0.1)

  if 0:
    os.system('ls -l /proc/%s/fd' % os.getpid())

  if 0:
    ctrl_z(sh)
  else:
    stop_process__hack('cat')

  sh.expect('.*Stopped.*')

  #sh.expect("\r\n\\[PID \\d+\\] Stopped")

  sh.sendline('')  # needed for dash

  expect_prompt(sh)

  sh.sendline('fg')

  if sh.shell_label == 'osh':
    sh.expect(r'Continue PID \d+')
  else:
    sh.expect('cat')

  # Ctrl-C to terminal
  ctrl_c(sh)
  expect_prompt(sh)

  sh.sendline('fg')

  expect_no_job(sh)


@register()
def bug_721(sh):
  'Call fg twice after process exits (issue 721)'

  # This test seems flaky under bash for some reason

  expect_prompt(sh)
  sh.sendline('cat')

  time.sleep(0.1)

  ctrl_c(sh)
  expect_prompt(sh)

  sh.sendline('fg')
  expect_no_job(sh)

  #sh.sendline('')
  #expect_prompt(sh)

  sh.sendline('fg')
  expect_no_job(sh)

  expect_prompt(sh)


@register()
def bug_1005(sh):
  'sleep 10 then Ctrl-Z then wait should not hang (issue 1005)'

  expect_prompt(sh)

  sh.sendline('sleep 10')

  time.sleep(0.1)

  ctrl_z(sh)
  sh.expect(r'.*Stopped.*')

  sh.sendline('wait')
  sh.sendline('echo status=$?')
  sh.expect(r"status=0")


@register()
def stopped_process(sh):
  'Resuming a stopped process'
  expect_prompt(sh)

  sh.sendline('cat')

  time.sleep(0.1)  # seems necessary

  if 0:
    ctrl_z(sh)
  else:
    stop_process__hack('cat')

  sh.expect('.*Stopped.*')

  sh.sendline('')  # needed for dash for some reason
  expect_prompt(sh)

  sh.sendline('fg')

  if sh.shell_label == 'osh':
    sh.expect(r'Continue PID \d+')
  else:
    sh.expect('cat')

  ctrl_c(sh)
  expect_prompt(sh)

  sh.sendline('fg')
  expect_no_job(sh)


@register()
def stopped_pipeline(sh):
  'Resuming a stopped pipeline (issue 1087)'
  expect_prompt(sh)

  sh.sendline('sleep 10 | cat | cat')

  time.sleep(0.1)  # seems necessary

  ctrl_z(sh)
  # stop_process__hack doesn't work here

  sh.expect('.*Stopped.*')

  sh.sendline('')  # needed for dash for some reason
  expect_prompt(sh)

  sh.sendline('fg')

  if sh.shell_label == 'osh':
    sh.expect(r'Continue PID \d+')
  else:
    sh.expect('cat')

  ctrl_c(sh)
  expect_prompt(sh)

  sh.sendline('fg')
  expect_no_job(sh)


if __name__ == '__main__':
  try:
    sys.exit(harness.main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
