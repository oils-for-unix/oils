#!/usr/bin/env python2
from __future__ import print_function
"""
read_from_fd.py
"""

import os
import sys


def main(argv):
  # Note: the shell has to open this fd
  for arg in sys.argv[1:]:
    fd = int(arg)
    #print 'reading from', fd
    try:
      in_str = os.read(fd, 1024)
    except OSError as e:
      print('FATAL: Error reading from fd %d: %s' % (fd, e), file=sys.stderr)
      sys.exit(1)

    s = '%d: ' % fd
    sys.stdout.write(s.encode('utf-8'))
    sys.stdout.write(in_str)  # write binary data to stdout


if __name__ == '__main__':
  main(sys.argv)
