#!/usr/bin/env python2
"""
time.py -- Replacement for coreutils 'time'.

The interface of this program is modelled after:

/usr/bin/time --append --output foo.txt --format '%x %e'

Problems with /usr/bin/time:
- Elapsed time only has 2 digits of precision.  Apparently it uses times()
  rather than getrusage()?  https://unix.stackexchange.com/questions/70653/increase-e-precision-with-usr-bin-time-shell-command 

Problems with resource.getrusage() in Python:

  The memory usage of dash and bash get obscured by Python!  Because
  subprocess.call() does a fork(), which includes Python's address space.
  # https://stackoverflow.com/questions/13880724/python-getrusage-with-rusage-children-behaves-stangely

Problems with bash time builtin
- has no way to get the exit code
- writes to stderr, so you it's annoying to get both process stderr and the
  timing

This program also writes CSV and TSV directly.
- CSV values get escaped
- TSV values can't have tabs

Real solution: Write a tiny C program to do it, and ditch /usr/bin/time.
"""
from __future__ import print_function

import csv
import optparse
import os
import sys
import subprocess
import time


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def Options():
  """Returns an option parser instance."""
  p = optparse.OptionParser('time.py [options] ARGV...')
  p.add_option(
      '--tsv', dest='tsv', default=False, action='store_true',
      help='Write output in TSV format')
  p.add_option(
      '--rusage', dest='rusage', default=False, action='store_true',
      help='Also show user time, system time, and max resident set size')
  p.add_option(
      '-o', '--output', dest='output', default=None,
      help='Name of output file to write to to')
  p.add_option(
      '-a', '--append', dest='append', default=False, action='store_true',
      help='Append to the file instead of overwriting it')
  p.add_option(
      '--field', dest='fields', default=[], action='append',
      help='A string to append to each row, after the exit code and status')
  p.add_option(
      '--time-fmt', dest='time_fmt', default='%.4f',
      help='sprintf format for elapsed seconds (float)')
  p.add_option(
      '--stdout', dest='stdout', default=None,
      help='Save stdout to this file, and add a column for its md5 checksum')
  return p


def main(argv):
  (opts, child_argv) = Options().parse_args(argv[1:])

  if not child_argv:
    raise RuntimeError('Expected a command')

  # %x: exit status
  # %e: elapsed
  fmt_parts = ['%x', '%e']

  if opts.rusage:
    # %U: user time
    # %S: sys time
    # %M: Max RSS
    fmt_parts.extend(['%U', '%S', '%M'])

  # Used only for 'time' format string.  For --field, we use our own.
  sep = '\t' if opts.tsv else ','
  fmt = sep.join(fmt_parts)

  time_argv = ['time', '--format', fmt]
  if opts.append:
    time_argv.append('--append')
  if opts.output:
    time_argv.extend(['--output', opts.output])
  time_argv.append('--')
  time_argv.extend(child_argv)
  #log('time_argv %s', time_argv)

  start_time = time.time()
  try:
    if opts.stdout:
      # We don't want to intermingle 'time' stdout with the program's stdout
      if not opts.output:
        raise RuntimeError('Flag -o is required when --stdout')
      with open(opts.stdout, 'w') as f:
        exit_code = subprocess.call(time_argv, stdout=f)
    else:
      exit_code = subprocess.call(time_argv)
  except OSError as e:
    log('Error executing %s: %s', time_argv, e)
    return 1

  elapsed = time.time() - start_time
  if opts.stdout:
    import md5
    m = md5.new()
    with open(opts.stdout) as f:
      while True:
        chunk = f.read(4096)
        if not chunk:
          break
        m.update(chunk)
    maybe_stdout = [m.hexdigest()]
  else:
    maybe_stdout = []  # no field

  more_cells = maybe_stdout + opts.fields

  if more_cells:
    if opts.output:
      with open(opts.output, 'r+') as f:  # read/write to seek and modify
        # Hack: overwrite the newline that 'time' wrote!
        f.seek(-1, os.SEEK_END)
        f.write(sep)

        if opts.tsv:
          # TSV output.
          out = csv.writer(f, delimiter='\t', lineterminator='\n',
                           doublequote=False,
                           quoting=csv.QUOTE_NONE)
        else:
          out = csv.writer(f)
        out.writerow(more_cells)
    else:
      log("Rows that -o would have written: %s", row)

  # Preserve the command's exit code.  (This means you can't distinguish
  # between a failure of time.py and the command, but that's better than
  # swallowing the error.)
  return exit_code


if __name__ == '__main__':
  try:
    status = main(sys.argv)
  except RuntimeError as e:
    log('time_.py: %s', e)
    status = 2
  sys.exit(status)
