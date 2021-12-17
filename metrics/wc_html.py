#!/usr/bin/env python2
"""
wc_html.py

Filter for HTML
"""
from __future__ import print_function

import sys


def main(argv):
  total = None
  rows = []

  # Parse
  for line in sys.stdin:
    line = line.strip()
    count, rel_path = line.split(None, 1)
    count = int(count)

    if rel_path == 'total':
      total = count
    else:
      rows.append((count, rel_path))

  # Print

  # TODO:
  # - Make this a button
  # - Do we need a unique CSS ID?  Maybe just hash the input

  print('<p>TOTAL {:,}</p>'.format(total))

  print('<div class="collapse">')

  # TODO:
  # - Could make a table out of this
  # - Link path to source code

  print('<pre>')
  for count, rel_path in rows:
    count_str = '{:,}'.format(count)
    print('%10s %s' % (count_str, rel_path))
  print('</pre>')
  print('</div>')



if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
