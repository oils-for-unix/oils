#!/usr/bin/env python3
"""
spec/stateful/job_control.py
"""
from __future__ import print_function

import signal
import sys
import time

import harness
from harness import register, expect_prompt
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
  if 'osh' in sh.shell_label:
    sh.expect('No job to put in the foreground')
  elif sh.shell_label == 'dash':
    sh.expect('.*fg: No current job')
  elif sh.shell_label == 'bash':
    sh.expect('.*fg: current: no such job.*')
  else:
    raise AssertionError()


def expect_continued(sh):
  if 'osh' in sh.shell_label:
    sh.expect(r'Continue PID \d+')
  else:
    sh.expect('cat')


@register()
def bug_1004(sh):
  'fg twice should not result in fatal error (issue 1004)'

  expect_prompt(sh)
  sh.sendline('cat')

  time.sleep(0.1)

  debug = False
  #debug = True

  if debug:
    import os
    #os.system('ls -l /proc/%s/fd' % os.getpid())

    # From test/group-session.sh
    log('harness PID = %d', os.getpid())
    import subprocess
    #os.system('ps -o pid,ppid,pgid,sid,tpgid,comm')

    # the child shell is NOT LISTED here because it's associated WITH A
    # DIFFERENT TERMINAL.
    subprocess.call(['ps', '-o', 'pid,ppid,pgid,sid,tpgid,comm'])

  ctrl_z(sh)

  sh.expect('.*Stopped.*')

  #sh.expect("\r\n\\[PID \\d+\\] Stopped")

  sh.sendline('')  # needed for dash
  expect_prompt(sh)

  sh.sendline('fg')
  if 'osh' in sh.shell_label:
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

  sh.sendline('')
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
  sh.expect('status=0')


@register(skip_shells=['dash'])
def bug_1005_wait_n(sh):
  'sleep 10 then Ctrl-Z then wait -n should not hang'

  expect_prompt(sh)

  sh.sendline('sleep 10')

  time.sleep(0.1)
  ctrl_z(sh)

  sh.expect(r'.*Stopped.*')

  sh.sendline('wait -n')
  sh.sendline('echo status=$?')
  sh.expect('status=127')


@register()
def stopped_process(sh):
  'Resuming a stopped process'
  expect_prompt(sh)

  sh.sendline('cat')

  time.sleep(0.1)  # seems necessary

  ctrl_z(sh)

  sh.expect('.*Stopped.*')

  sh.sendline('')  # needed for dash for some reason
  expect_prompt(sh)

  sh.sendline('fg')

  if 'osh' in sh.shell_label:
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

  sh.expect('.*Stopped.*')

  sh.sendline('')  # needed for dash for some reason
  expect_prompt(sh)

  sh.sendline('fg')

  if 'osh' in sh.shell_label:
    sh.expect(r'Continue PID \d+')
  else:
    sh.expect('cat')

  ctrl_c(sh)
  expect_prompt(sh)

  sh.sendline('fg')
  expect_no_job(sh)


@register()
def cycle_process_bg_fg(sh):
  'Suspend and resume a process several times'
  expect_prompt(sh)

  sh.sendline('cat')
  time.sleep(0.1)  # seems necessary

  for _ in range(3):
    ctrl_z(sh)
    sh.expect('.*Stopped.*')
    sh.sendline('')  # needed for dash for some reason
    expect_prompt(sh)
    sh.sendline('fg')
    expect_continued(sh)

  ctrl_c(sh)
  expect_prompt(sh)

  sh.sendline('fg')
  expect_no_job(sh)


@register()
def suspend_status(sh):
  'Ctrl-Z and then look at $?'

  # This test seems flaky under bash for some reason

  expect_prompt(sh)
  sh.sendline('cat')

  time.sleep(0.1)

  ctrl_z(sh)
  expect_prompt(sh)

  sh.sendline('echo status=$?')
  sh.expect('status=148')
  expect_prompt(sh)


@register(skip_shells=['zsh'])
def no_spurious_tty_take(sh):
  'A background job getting stopped (e.g. by SIGTTIN) or exiting should not disrupt foreground processes'
  expect_prompt(sh)

  sh.sendline('cat &') # stop
  sh.sendline('sleep 0.1 &') # exit
  expect_prompt(sh)

  # background cat should have been stopped by SIGTTIN immediately, but we don't
  # hear about it from wait() until the foreground process has been started because
  # the shell was blocked in readline when the signal fired.
  sh.sendline('python2 -c "import sys; print(sys.stdin.readline().strip() + \'bar\')"')
  time.sleep(0.1)  # seems necessary
  if 'osh' in sh.shell_label:
    # Quirk of osh. TODO: supress this print for background jobs?
    sh.expect('.*Stopped.*')

  # foreground procoess should not have been stopped.
  sh.sendline('foo')
  sh.expect('foobar')

  ctrl_c(sh)
  expect_prompt(sh)


if __name__ == '__main__':
  try:
    sys.exit(harness.main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
