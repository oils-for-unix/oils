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
  p = optparse.OptionParser('tsv_column_from_files.py FLAG* FILE')
  p.add_option(
      '--path-column', dest='path_column',
      help='The name of the column that has file system paths')
  p.add_option(
      '--new-column', dest='new_column',
      help='The name of the new column to create')
  p.add_option(
      '--extract-group-1', dest='extract_group_1',
      help="Search the file contents for this Python regex.  Then extract the first group")
  return p


def main(argv):
  p = Options()
  (opts, argv) = p.parse_args(argv[1:])

  # tsv_column_from_files.py \
  #   --path-column     cachegrind_out_path  \
  #   --new-column      I_refs \
  #   --extract-group-1 'I[ ]*refs:[ ]+([\d,]+)' \  # it extracts the first group
  #   foo.tsv 
  #
  # NOTE: QTT can allow commas like 1,000,000.  Like 1_000_000

  try:
    tsv_path = argv[0]
  except IndexError:
    p.print_usage()
    return 2

  base_dir = os.path.dirname(tsv_path)

  path_col_index = -1

  with open(tsv_path) as f:
    for i, line in enumerate(f):
      line = line.rstrip()

      row = line.split('\t')
      if i == 0:
        try:
          path_col_index = row.index(opts.path_column)
        except ValueError:
          raise RuntimeError('%r not found in %r' % (opts.path_column, row))
        print('%s\t%s' % (line, opts.new_column))
        continue  # skip to first row

      assert path_col_index != -1
      rel_path = row[path_col_index]

      cell_path = os.path.join(base_dir, rel_path)
      with open(cell_path) as f2:
        contents = f2.read()
        if opts.extract_group_1:
          pat = re.compile(opts.extract_group_1, re.VERBOSE)
          m = pat.search(contents)
          if not m:
            raise RuntimeError("Couldn't find %r in %r" % (opts.extract_group_1, contents))
          val = m.group(1)
          #print(repr(val))
        else:
          val = contents  # just use the whole file
      if '\t' in val or '\n' in val:
        raise RuntimeError("Found tab or newline in TSV cell %r" % val)
      print('%s\t%s' % (line, val))

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
