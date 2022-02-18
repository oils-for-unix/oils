#!/usr/bin/env python2
"""
fork_signal_state.py
"""
from __future__ import print_function

import os
import signal
import sys
import time


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def SignalState(pid):
  with open('/proc/%d/status' % pid) as f:
    for line in f:
      if line.startswith('Sig'):
        print(line, end='')


def main(argv):
  parent_pid = os.getpid()
  log('parent is %d', parent_pid)

  # Hm this looks like it works
  # Now why doesn't Ctrl-Z through the terminal work?  The process group should
  # be controlling the terminal

  # test/group-session.sh shows PGID and TPGID (controlling tty process group ID)

  log('===')
  SignalState(parent_pid)
  signal.signal(signal.SIGTSTP, signal.SIG_IGN)
  SignalState(parent_pid)
  log('===')

  line = raw_input()

  if line.startswith('sleep'):
    pid = os.fork()
    if pid == 0:
      child_pid = os.getpid()

      log('---')
      SignalState(child_pid)
      signal.signal(signal.SIGTSTP, signal.SIG_DFL)
      SignalState(child_pid)
      log('---')

      log('sleep 1 in child %d', child_pid)
      os.execve('/bin/sleep', ['sleep', '1'], {})

    elif pid < 0:
      raise AssertionError()

    else:
      log('parent spawned %d', pid)

      log('waiting')
      pid, status = os.waitpid(-1, os.WUNTRACED)
      log('wait => pid %d exited with status %d', pid, status)

      if os.WIFEXITED(status):
        log('EXITED')

      if os.WIFSIGNALED(status):
        log('SIGNALED')

      elif os.WIFSTOPPED(status):
        log('STOPPED')

  else:
    log('BAD COMMAND')


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
