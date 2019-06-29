#!/usr/bin/env python2
"""
csv_concat.py
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
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
