#!/usr/bin/env python2
"""
time.py -- Replacement for coreutils 'time'.

TODO:
(Must be Python 3 because it's used before a Python 2 WEDGE can be installed.)

The interface of this program is modelled after:

/usr/bin/time --append --output foo.txt --format '%x %e'

Why we're not using /usr/bin/time:
- We need to print extra TSV fields at the end of the row, but it prints a newline
- It prints extraneous output: 'Command exited with non-zero status 1'
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

So we use a tiny C program time-helper.c to do it, and not /usr/bin/time.
"""
from __future__ import print_function

import csv
#import hashlib  # python 3
import md5
import optparse
import os
import sys
import subprocess
import time

THIS_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))

time1 = os.path.abspath(os.path.join(THIS_DIR, '../_devbuild/bin/time-helper'))
# Pre-built one
time2 = '/wedge/oils-for-unix.org/pkg/time-helper/2023-02-28/time-helper'

if os.path.exists(time1):
  TIME_HELPER = time1
elif os.path.exists(time2):
  TIME_HELPER = time2
else:
  raise AssertionError('time-helper not found')


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
  p.add_option(
      '--print-header', dest='print_header', default=False, action='store_true',
      help='Print an XSV header, respecting --rusage, --stdout, --field, and --tsv')
  return p


def MakeTableOutput(f, tsv):
  if tsv:  # TSV output.
    out = csv.writer(f, delimiter='\t', lineterminator='\n',
                     doublequote=False,
                     quoting=csv.QUOTE_NONE)
  else:
    out = csv.writer(f)
  return out


def main(argv):
  (opts, child_argv) = Options().parse_args(argv[1:])

  # Used only for 'time' format string.  For --field, we use our own.
  sep = '\t' if opts.tsv else ','

  if opts.print_header:
    if child_argv:
      raise RuntimeError('No arguments allowed with --print-header')
    names = ['status', 'elapsed_secs']
    if opts.rusage:
      names.extend(['user_secs', 'sys_secs', 'max_rss_KiB'])
    if opts.stdout:
      names.append('stdout_md5sum')
    names.extend(opts.fields)

    if opts.output:
      f = open(opts.output, 'w')
    else:
      f = sys.stdout
    table_out = MakeTableOutput(f, opts.tsv)
    table_out.writerow(names)
    return 0

  if not child_argv:
    raise RuntimeError('Expected a command')

  # built by build/dev.sh all
  time_argv = [TIME_HELPER, '-d', sep]

  if opts.append:
    time_argv.append('-a')

  if opts.output:
    time_argv.extend(['-o', opts.output])

  # %x: exit status
  # %e: elapsed
  time_argv.extend(['-x', '-e'])
  if opts.rusage:
    # %U: user time
    # %S: sys time
    # %M: Max RSS
    time_argv.extend(['-U', '-S', '-M'])

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
    #m = hashlib.md5()  # python 3
    m = md5.new()
    with open(opts.stdout, 'rb') as f:
      while True:
        chunk = f.read(4096)
        if not chunk:
          break
        m.update(chunk)
    maybe_stdout = [m.hexdigest()]
  else:
    maybe_stdout = []  # no field

  more_cells = maybe_stdout + opts.fields

  if opts.output:
    with open(opts.output, 'a') as f:  # append
      if more_cells:
        f.write(sep)  # tab or comma for more cells
        table_out = MakeTableOutput(f, opts.tsv)
        table_out.writerow(more_cells)
      else:
        f.write('\n')   # end the row
  else:
    if more_cells:
      log("More cells that -o would have written: %s", more_cells)

  # Preserve the command's exit code.  (This means you can't distinguish
  # between a failure of time.py and the command, but that's better than
  # swallowing the error.)
  return exit_code


if __name__ == '__main__':
  try:
    status = main(sys.argv)
  except KeyboardInterrupt as e:
    print('%s: interrupted with Ctrl-C' % sys.argv[0], file=sys.stderr)
    sys.exit(1)
  except RuntimeError as e:
    log('time_.py: %s', e)
    status = 2
  sys.exit(status)
