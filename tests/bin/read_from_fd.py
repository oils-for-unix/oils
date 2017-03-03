#!/usr/bin/python
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
      print >>sys.stderr, 'FATAL: Error reading from fd %d: %s' % (fd, e)
      sys.exit(1)
    sys.stdout.write('%d: %s' % (fd, in_str))


if __name__ == '__main__':
  main(sys.argv)
