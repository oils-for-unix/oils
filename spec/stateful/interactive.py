#!/usr/bin/env python3
"""
interactive.py
"""
from __future__ import print_function

import sys
import time

import harness
from harness import register, expect_prompt


@register()
def syntax_error(sh):
  'syntax error makes status=2'

  sh.sendline('syntax ) error')

  #time.sleep(0.1)

  expect_prompt(sh)

  sh.sendline('echo status=$?')

  if sh.shell_label == 'mksh':
    # mksh gives status=1, and zsh doesn't give anything?
    sh.expect('status=1')
  else:
    sh.expect('status=2')  # osh, bash, dash


@register()
def bg_proc_notify(sh):
  'notification about background process (issue 1093)'

  expect_prompt(sh)

  sh.sendline('sleep 0.1 &')
  sh.sendline('sleep 0.3 &')

  if sh.shell_label == 'bash':
    # e.g. [1] 12345
    # not using trailing + because pexpect doc warns about that case
    # dash doesn't print this
    sh.expect(r'\[\d+\]')

  expect_prompt(sh)

  # Wait until after it stops and then hit enter
  time.sleep(0.4)
  sh.sendline('')
  sh.expect(r'.*Done.*')
  sh.sendline('')
  sh.expect(r'.*Done.*')

  sh.sendline('echo status=$?')
  sh.expect('status=0')

@register()
def bg_pipeline_notify(sh):
  'notification about background pipeline (issue 1093)'

  expect_prompt(sh)

  sh.sendline('sleep 0.1 | cat &')

  if sh.shell_label == 'bash':
    # e.g. [1] 12345
    # not using trailing + because pexpect doc warns about that case
    # dash doesn't print this
    sh.expect(r'\[\d+\]')

  expect_prompt(sh)

  time.sleep(0.2)
  sh.sendline('')
  if 'osh' in sh.shell_label:
      # need to wake up from wait() twice in osh
      # TODO: can we avoid this? how do bash and others handle this?
      expect_prompt(sh)
      sh.sendline('')

  sh.expect(r'.*Done.*')

  sh.sendline('echo status=$?')
  sh.expect('status=0')


if __name__ == '__main__':
  try:
    sys.exit(harness.main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
