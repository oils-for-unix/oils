#!/usr/bin/env python2
"""
count_procs.py

Print a results table.

Input looks like

01 osh
01 osh
01 dash
01 dash
...

"""
from __future__ import print_function

import collections
import sys

from core import ansi


def Color(i):
  #return str(i)
  return '*' * i


# TODO:
# - Print the test snippet somewhere

def main(argv):
  code_strs = {}
  with open(argv[1]) as f:
    for line in f:
      case_id, code_str = line.split(None, 1)
      code_strs[case_id] = code_str

  cases = set()
  shells = set()

  d = collections.defaultdict(int)
  for line in sys.stdin:
    case, sh = line.split()

    cases.add(case)
    shells.add(sh)

    d[case, sh] += 1

  f = sys.stdout

  f.write("\t")
  for sh in sorted(shells):
    f.write(sh + "\t")
  f.write('result\t')
  f.write('code')
  f.write("\n")

  for case_id  in sorted(cases):
    f.write(case_id + "\t")
    min_procs = 20
    for sh in sorted(shells):
      num_procs = d[case_id, sh]
      f.write(Color(num_procs) + "\t")
      min_procs = min(num_procs, min_procs)

    osh_count = d[case_id, 'osh']
    if osh_count != min_procs:
      f.write('%sx%s %d>%d\t' % (
        ansi.RED + ansi.BOLD, ansi.RESET, osh_count, min_procs))
    else:
      f.write('\t')

    f.write(code_strs[case_id])


    f.write("\n")


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)

