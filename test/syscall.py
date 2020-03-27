#!/usr/bin/env python2
"""
count_procs.py

Print a results table.

Input looks like

01-dash
01-dash
01-osh
01-osh
01-osh
...

"""
from __future__ import print_function

import collections
import re
import sys


def Cell(i):
  """Visually show number of processes.

  ^  ^^  ^^^  etc.
  """
  s = '^' * i
  return '%6s' % s


# lines look like this:
#
# 554  01-osh.1234
# 553  01-osh.1235

WC_LINE = re.compile(r'''
\s*  
(\d+)     # number of lines
\s+
(\d{2})   # case ID
-
([a-z]+)  # shell name
''', re.VERBOSE)

assert WC_LINE.match('    68 01-ash.19610')

# TODO:
# - Print the test snippet somewhere

def main(argv):
  code_strs = {}
  with open(argv[1]) as f:
    for line in f:
      case_id, code_str = line.split(None, 1)  # whitespace
      code_strs[case_id] = code_str

  cases = set()
  shells = set()

  num_procs = collections.defaultdict(int)
  procs_by_shell = collections.defaultdict(int)

  num_syscalls = collections.defaultdict(int)
  syscalls_by_shell = collections.defaultdict(int)

  for line in sys.stdin:
    m = WC_LINE.match(line)
    if not m:
      raise RuntimeError('Invalid line %r' % line)
    num_sys, case, sh = m.groups()
    num_sys = int(num_sys)

    cases.add(case)
    shells.add(sh)

    num_procs[case, sh] += 1
    num_syscalls[case, sh] += num_sys

    procs_by_shell[sh] += 1
    syscalls_by_shell[sh] += num_sys

  f = sys.stdout

  # Orders for shells
  proc_sh = sorted(procs_by_shell, key=lambda sh: procs_by_shell[sh])
  syscall_sh = sorted(syscalls_by_shell, key=lambda sh: syscalls_by_shell[sh])
  #print(proc_sh)
  #print(syscall_sh)

  # Print Number of processes

  f.write('Number of Processes Started, by shell and code string\n\n')

  def WriteHeader(shells):
    f.write("\t")
    for sh in shells:
      f.write("%6s\t" % sh)
    f.write('osh>min\t')
    f.write('code')
    f.write("\n")

  WriteHeader(proc_sh)

  for case_id in sorted(cases):
    f.write(case_id + "\t")
    min_procs = 20
    for sh in proc_sh:
      n = num_procs[case_id, sh]
      f.write(Cell(n) + "\t")
      min_procs = min(n, min_procs)

    osh_count = num_procs[case_id, 'osh']
    if osh_count != min_procs:
      f.write('%d>%d\t' % (osh_count, min_procs))
    else:
      f.write('\t')

    f.write(code_strs[case_id])
    f.write("\n")

  f.write("TOTAL\t")
  for sh in proc_sh:
    f.write('%6d\t' % procs_by_shell[sh])
  f.write('\n\n')


  #
  # Print
  #

  f.write('Number of Syscalls\n\n')

  WriteHeader(syscall_sh)

  for case_id in sorted(cases):
    f.write(case_id + "\t")
    #min_procs = 20
    for sh in syscall_sh:
      n = num_syscalls[case_id, sh]
      f.write('%6d\t' % n)
      #min_procs = min(n, min_procs)

    #osh_count = num_procs[case_id, 'osh']
    if False: #osh_count != min_procs:
      f.write('%sx%s %d>%d\t' % (L, R, osh_count, min_procs))
    else:
      f.write('\t')

    f.write(code_strs[case_id])
    f.write("\n")

  f.write("TOTAL\t")
  for sh in syscall_sh:
    f.write('%6d\t' % syscalls_by_shell[sh])
  f.write('\n\n')


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)

