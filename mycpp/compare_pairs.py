#!/usr/bin/env python2
"""
compare_pairs.py
"""
from __future__ import print_function

import subprocess
import sys

def Check(left, right):
  with open(left) as f1, open(right) as f2:
    b1 = f1.read()
    b2 = f2.read()

  if b1 != b2:
    print("%s != %s" % (left, right))
    sys.stdout.flush()  # prevent interleaving

    # Only invoke a subprocess when they are NOT equal
    subprocess.call(["diff", "-u", left, right])
    return False

  return True

def main(argv):
  num_failures = 0

  paths = argv[1:]
  n = len(paths)
  i = 0
  while i < n:
    log_path = paths[i]
    py_path = paths[i+1]

    #print(log_path, py_path)

    if not Check(log_path, py_path):
      num_failures += 1
    else:
      print("OK %s" % log_path)
      print("   %s" % py_path)
      #sys.stdout.flush()

    i += 2

  if num_failures != 0:
    print("logs-equal: %d failures" % num_failures)
    return 1

  return 0


if __name__ == '__main__':
  try:
    sys.exit(main(sys.argv))
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
