#!/usr/bin/python
"""
scrape_flags.py
"""
from __future__ import print_function

import json
import re
import sys

# NOTE: Could remove trailing punctuation like ; ?

# 2 spaces, otherwise we get two --sort in ls
LONG_FLAG_RE = re.compile(r'''
  [  ].*
  (?P<flag>--[a-zA-Z0-9-]+)
  (?P<arg>=\w+)?
  \s+
  (?P<desc>.*)
''', re.VERBOSE)


def main(argv):
  flags = []
  num_flags = 0
  for line in sys.stdin:
    m = LONG_FLAG_RE.match(line)
    if m:
      flags.append(m.groupdict())
      print('%s%s\t%s' % (
        m.group('flag'),
        '=' if m.group('arg') else '',
        m.group('desc')
      ))
      num_flags += 1

  print('Summary: %d flags scraped' % num_flags, file=sys.stderr)

  #json.dump(flags, sys.stdout, indent=2)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
