#!/usr/bin/env python2
"""
pyreadline.py

TODO: Set up history/completion, and then strace.  Where is the canonical example?

NOTE: InteractiveLineReader does use raw_input().  Should it use something
else?

"""
from __future__ import print_function

import sys
import readline


def main(argv):
  try:
    prompt_str = argv[1]
  except IndexError:
    prompt_str = '! '
  import os
  readline.parse_and_bind("tab: complete")
  print('PID %d' % os.getpid())
  while True:
    x = raw_input(prompt_str)
    print(x)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
