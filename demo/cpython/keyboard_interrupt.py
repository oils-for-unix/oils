#!/usr/bin/env python2
"""
keyboard_interrupt.py: How to replace KeyboardInterrupt
"""
from __future__ import print_function

import signal
import sys
import time



g_sigint = False

def SigInt(x, y):
  print('SIGINT')
  global g_sigint
  g_sigint = True


def main(argv):

  # This suppresses KeyboardInterrupt.  You can still do Ctrl-\ or check a flag
  # and throw your own exception.
  signal.signal(signal.SIGINT, SigInt)

  while True:
    print('----')
    time.sleep(0.5)
    if g_sigint:
      raise Exception('interrupted')


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
