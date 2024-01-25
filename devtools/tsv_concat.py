#!/usr/bin/env python2
from __future__ import print_function
"""
tsv_concat.py - Also run with Python 3
"""
import sys

def main(argv):
  first_header = None
  for path in argv[1:]:
    with open(path) as f:
      # Assume there's no quoting or escaping.
      header = f.readline()
      if first_header is None:
        sys.stdout.write(header)
        first_header = header.strip()
      else:
        h = header.strip()
        if h != first_header:
          raise RuntimeError(
              'Invalid header in %r: %r.  Expected %r' % (path, h,
              first_header))
      # Now print rest of lines
      for line in f:
        sys.stdout.write(line)



if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
