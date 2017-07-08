#!/usr/bin/env python
"""
show_fd_table.py -- Uses Linux-specific proc interface
"""

import os
import sys


def main(argv):
  d = '/proc/self/fd/'
  for fd in os.listdir(d):
    path = os.path.join(d, fd)
    try:
      connected_to = os.readlink(path)
    except OSError as e:
      print fd, str(e)
    else:
      print fd, connected_to


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
