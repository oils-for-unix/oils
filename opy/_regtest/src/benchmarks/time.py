#!/usr/bin/env python
"""
time.py -- Replacement for coreutils 'time'.

The interface of this program is modelled after:

/usr/bin/time --append --output foo.txt --format '%x %e'

Problems with /usr/bin/time:
  - elapsed time only has 2 digits of precision

Problems with bash time builtin
  - has no way to get the exit code
  - writes to stderr, so you it's annoying to get both process stderr and
    and

This program also writes CSV directly, so you can have commas in fields, etc.
"""

import csv
import optparse
import sys
import subprocess
import time


def Options():
  """Returns an option parser instance."""
  p = optparse.OptionParser('time.py [options] ARGV...')
  p.add_option(
      '--tsv', dest='tsv', default=False, action='store_true',
      help='Write output in TSV format')
  p.add_option(
      '-o', '--output', dest='output', default=None,
      help='Name of output file to write to')
  p.add_option(
      '--field', dest='fields', default=[], action='append',
      help='A string to append to each row, after the exit code and status')
  return p


def main(argv):
  (opts, child_argv) = Options().parse_args(argv[1:])

  start_time = time.time()
  exit_code = subprocess.call(child_argv)
  elapsed = time.time() - start_time

  fields = tuple(opts.fields)
  with open(opts.output, 'a') as f:
    if opts.tsv:
      # TSV output.
      out = csv.writer(f, delimiter='\t', doublequote=False,
                       quoting=csv.QUOTE_NONE)
    else:
      out = csv.writer(f)
    row = (exit_code, '%.4f' % elapsed) + fields
    out.writerow(row)

  # Preserve the command's exit code.  (This means you can't distinguish
  # between a failure of time.py and the command, but that's better than
  # swallowing the error.)
  return exit_code


if __name__ == '__main__':
  sys.exit(main(sys.argv))
