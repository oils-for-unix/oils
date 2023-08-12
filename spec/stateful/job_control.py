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

PYCAT = 'python2 -c "import sys; print(sys.stdin.readline().strip() + \'%s\')"'


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


# OSH doesn't support this because of the lastpipe issue
# Note: it would be nice to print a message on Ctrl-Z like zsh does:
# "job can't be suspended"

@register(not_impl_shells=['osh', 'osh-cpp'])
def stopped_pipeline(sh):
  'Suspend and resume a pipeline (issue 1087)'

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
  time.sleep(0.1) # TODO: need to wait a bit for jobs to get SIGTTIN. can we be more precise?
  sh.sendline(PYCAT % 'bar')
  if 'osh' in sh.shell_label:
    # Quirk of osh. TODO: suppress this print for background jobs?
    sh.expect('.*Stopped.*')

  # foreground process should not have been stopped.
  sh.sendline('foo')
  sh.expect('foobar')

  ctrl_c(sh)
  expect_prompt(sh)


@register()
def fg_current_previous(sh):
  'Resume the special jobs: %- and %+'
  expect_prompt(sh)

  sh.sendline('sleep 1000 &') # will be terminated as soon as we're done with it

  # Start two jobs. Both will get stopped by SIGTTIN when they try to read() on
  # STDIN. According to POSIX, %- and %+ should always refer to stopped jobs if
  # there are at least two of them.
  sh.sendline((PYCAT % 'bar') + ' &')

  time.sleep(0.1) # TODO: need to wait a bit for jobs to get SIGTTIN. can we be more precise?
  sh.sendline('cat &')
  if 'osh' in sh.shell_label:
    sh.expect('.*Stopped.*')

  time.sleep(0.1) # TODO: need to wait a bit for jobs to get SIGTTIN. can we be more precise?
  if 'osh' in sh.shell_label:
    sh.sendline('')
    sh.expect('.*Stopped.*')

  # Bring back the newest stopped job
  sh.sendline('fg %+')
  if 'osh' in sh.shell_label:
    sh.expect(r'Continue PID \d+')

  sh.sendline('foo')
  sh.expect('foo')
  ctrl_z(sh)

  # Bring back the second-newest stopped job
  sh.sendline('fg %-')
  if 'osh' in sh.shell_label:
    sh.expect(r'Continue PID \d+')

  sh.sendline('')
  sh.expect('bar')

  # Force cat to exit
  ctrl_c(sh)
  expect_prompt(sh)
  time.sleep(0.1) # wait for cat job to go away

  # Now that cat is gone, %- should refer to the running job
  sh.sendline('fg %-')
  if 'osh' in sh.shell_label:
    sh.expect(r'Continue PID \d+')

  sh.sendline('true')
  time.sleep(0.5)
  sh.expect('') # sleep should swallow whatever we write to stdin
  ctrl_c(sh)

  # %+ and %- should refer to the same thing now that there's only one job
  sh.sendline('fg %+')
  if 'osh' in sh.shell_label:
    sh.expect(r'Continue PID \d+')

  sh.sendline('woof')
  sh.expect('woof')
  ctrl_z(sh)
  sh.sendline('fg %-')
  if 'osh' in sh.shell_label:
    sh.expect(r'Continue PID \d+')

  sh.sendline('meow')
  sh.expect('meow')
  ctrl_c(sh)

  expect_prompt(sh)


@register(skip_shells=['dash'])
def fg_job_id(sh):
  'Resume jobs with integral job specs using `fg` builtin'
  expect_prompt(sh)

  sh.sendline((PYCAT % 'foo') + ' &') # %1

  time.sleep(0.1) # TODO: need to wait a bit for jobs to get SIGTTIN. can we be more precise?
  sh.sendline((PYCAT % 'bar') + ' &') # %2
  if 'osh' in sh.shell_label:
    sh.expect('.*Stopped.*')

  time.sleep(0.1)
  sh.sendline((PYCAT % 'baz') + ' &') # %3 and %-
  if 'osh' in sh.shell_label:
    sh.expect('.*Stopped.*')

  time.sleep(0.1)
  if 'osh' in sh.shell_label:
    sh.sendline('')
    sh.expect('.*Stopped.*')

  sh.sendline('')
  expect_prompt(sh)

  sh.sendline('fg %1')
  sh.sendline('')
  sh.expect('foo')

  sh.sendline('fg %3')
  sh.sendline('')
  sh.expect('baz')

  sh.sendline('fg %2')
  sh.sendline('')
  sh.expect('bar')


@register()
def wait_job_spec(sh):
  'Wait using a job spec'
  expect_prompt(sh)

  sh.sendline('(sleep 2; exit 11) &')
  sh.sendline('(sleep 1; exit 22) &')
  sh.sendline('(sleep 3; exit 33) &')

  time.sleep(1)
  sh.sendline('wait %2; echo status=$?')
  sh.expect('status=22')

  time.sleep(1)
  sh.sendline('wait %-; echo status=$?')
  sh.expect('status=11')

  time.sleep(1)
  sh.sendline('wait %+; echo status=$?')
  sh.expect('status=33')


if __name__ == '__main__':
  try:
    sys.exit(harness.main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
