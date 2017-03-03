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
    in_str = os.read(fd, 1024)
    sys.stdout.write('%d: %s' % (fd, in_str))


if __name__ == '__main__':
  main(sys.argv)
