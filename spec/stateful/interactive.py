#!/usr/bin/env python3
"""
interactive.py
"""
from __future__ import print_function

import sys

import harness
from harness import register


@register()
def t9(sh):
  'syntax error makes status=2'

  sh.sendline('syntax ) error')

  #time.sleep(0.1)

  sh.expect(r'.*\$')  # expect prompt

  sh.sendline('echo status=$?')
  sh.expect('status=2')  # osh, bash, dash

  # mksh gives status=1, and zsh doesn't give anything?


if __name__ == '__main__':
  try:
    sys.exit(harness.main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
