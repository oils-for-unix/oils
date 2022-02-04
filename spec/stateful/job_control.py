#!/usr/bin/env python3
"""
spec/stateful/job_control.py
"""
from __future__ import print_function

import fcntl
import pty
import signal
import sys
import time

import harness
from harness import register, stop_process__hack, send_signal, expect_prompt
from test.spec_lib import log


# Hint from Stevens book
#
# http://lkml.iu.edu/hypermail/linux/kernel/1006.2/02460.html
# "TIOCSIG Generate a signal to processes in the
# current process group of the pty."

# Generated from C header file
TIOCSIG = 0x40045436

@register()
def t6(sh):
  'fg twice should not result in fatal error (issue 1004)'

  expect_prompt(sh)
  sh.sendline('cat')

  time.sleep(0.1)

  if 0:
    os.system('ls -l /proc/%s/fd' % os.getpid())

  if 0:
    # TODO: Make this work for OSH!
    fcntl.ioctl(sh.child_fd, TIOCSIG, signal.SIGTSTP)
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

  if 1:
    # Ctrl-C to terminal
    fcntl.ioctl(sh.child_fd, TIOCSIG, signal.SIGINT)
  else:
    sh.sendintr()  # SIGINT

  expect_prompt(sh)
  sh.sendline('fg')

  if sh.shell_label == 'osh':
    sh.expect("No job to put in the foreground")
  elif sh.shell_label == 'dash':
    sh.expect('.*fg: No current job')
  elif sh.shell_label == 'bash':
    sh.expect('.*fg: current: no such job.*')
  else:
    raise AssertionError()


@register(skip_shells=['bash'])
def t7(sh):
  'Test resuming a killed process'
  expect_prompt(sh)
  sh.sendline('cat')
  stop_process__hack('cat')

  sh.expect("\r\n\\[PID \\d+\\] Stopped")
  expect_prompt(sh)

  sh.sendline('fg')
  sh.expect(r'Continue PID \d+')

  send_signal("cat", signal.SIGINT)
  expect_prompt(sh)

  sh.sendline('fg')
  sh.expect('No job to put in the foreground')


@register(skip_shells=['bash'])
def t8(sh):
  'Call fg after process exits (issue 721)'

  expect_prompt(sh)
  sh.sendline('cat')

  #osh.sendcontrol("c")
  sh.sendintr()  # SIGINT
  expect_prompt(sh)

  sh.sendline('fg')
  sh.expect("No job to put in the foreground")
  expect_prompt(sh)

  sh.sendline('fg')
  sh.expect('No job to put in the foreground')
  expect_prompt(sh)


@register()
def bug_1005(sh):
  'sleep 10 then Ctrl-Z then wait should not hang'

  expect_prompt(sh)

  return

  sh.sendline('sleep 10')

  # This is NOT right.  The Ctrl-Z goes to the TERMINAL, and the TERMINAL sends
  # it to both the shell process and the sleep process.  The shell process
  # should ignore it.

  # Section 19.6 of APUE: SIGTSTP can't be delivered to a process!!
  # Section 19.7: Signal generation with ioctl TIOCSIG!

  #sh.kill(signal.SIGTSTP)

  # This distribute Ctrl-Z to the whole process group?  Why doesn't it work?
  sh.sendcontrol('z')
  sh.expect(r'.*Stopped.*')

  #sh.expect(r'\^Z')

  return
  sh.sendline('wait')
  sh.sendline('echo status=$?')
  sh.expect(r"status=0")


if __name__ == '__main__':
  try:
    sys.exit(harness.main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
