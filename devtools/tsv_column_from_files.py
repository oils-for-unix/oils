#!/usr/bin/env python2
"""
tsv_column_from_files.py

- Read a TSV file on stdin, and take a series of transformations.
- A transformation consists of
  - a source column name, which contains file system paths
  - optional --base-dir
  - a new column name
  - a regex to extract from the files



"""
from __future__ import print_function

import csv
import optparse
import os
import re
import sys


def Options():
  """Returns an option parser instance."""
  p = optparse.OptionParser('time.py [options] ARGV...')
  p.add_option(
      '--tsv', dest='tsv', default=False, action='store_true',
      help='Write output in TSV format')


  # TODO: Take the path directly rather than reading from stdin.
  # Then we have a base dir

  p.add_option(
      '--base-dir', dest='base_dir', default='',
      help='For resolving relative paths')
  return p


def main(argv):
  (opts, child_argv) = Options().parse_args(argv[1:])

  path_col_name = argv[1]
  new_col_name = argv[2]
  pattern = argv[3]  # re.search

  path_col_index = -1

  for i, line in enumerate(sys.stdin):
    row = line.rstrip().split('\t')
    if i == 0:
      try:
        path_col_index = row.index(path_col_name)
      except ValueError:
        raise RuntimeError('%r not found in %r' % (path_col_name, row))
      continue

    rel_path = row[path_col_index]
    print(rel_path)

    path = os.path.join(opts.base_dir, rel_path)

    with open(path) as f:
      contents = f.read()


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
