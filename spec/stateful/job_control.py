#!/usr/bin/env python3
"""
interactive.py
"""
from __future__ import print_function

import signal
import sys

import harness
from harness import register, stop_process__hack, send_signal


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


if __name__ == '__main__':
  try:
    harness.main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
