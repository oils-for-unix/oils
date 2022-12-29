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


def _PrintNewRow(row, path_col_index, new_val):
  """Print a row, replacing the cell in one column."""
  for i, cell in enumerate(row):
    if i != 0:
      print('\t', end='')

    if i == path_col_index:
      print(new_val, end='')
    else:
      print(row[i], end='')
  print()


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
  p.add_option(
      '--remove-commas', dest='remove_commas', action='store_true',
      help='Remove commas from the value after --extract-group1')
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
          raise RuntimeError('Expected %r in header %r' % (opts.path_column, row))
        _PrintNewRow(row, path_col_index, opts.new_column)
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

          if opts.remove_commas:  # annoying hack for cachegrind output
            val = val.replace(',', '')

          #print(repr(val))
        else:
          val = contents  # just use the whole file
      if '\t' in val or '\n' in val:
        raise RuntimeError("Found tab or newline in TSV cell %r" % val)

      _PrintNewRow(row, path_col_index, val)

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError as e:
    print('%s FATAL: %s' % (sys.argv[0], e), file=sys.stderr)
    sys.exit(1)
