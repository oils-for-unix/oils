#!/usr/bin/env python2
"""
schema2sqlite.py
"""
from __future__ import print_function

import csv
import optparse
import sys

import csv2html


def CreateOptionsParser():
  p = optparse.OptionParser()

  return p


def main(argv):
  (opts, argv) = CreateOptionsParser().parse_args(argv[1:])

  try:
    schema_path = argv[0]
  except IndexError:
    raise RuntimeError('Expected schema TSV filename.')

  try:
    schema_f = open(schema_path)
  except IOError as e:
    raise RuntimeError('Error opening schema: %s' %  e)

  r = csv.reader(schema_f, delimiter='\t', doublequote=False,
                 quoting=csv.QUOTE_NONE)
  schema = csv2html.Schema(list(r))

  print(schema.ToSqlite())


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
