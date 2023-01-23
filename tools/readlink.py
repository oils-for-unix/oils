from __future__ import print_function
"""
readlink.py - Minimal implementation of readlink -f, e.g. for OS X.
"""

import libc
from frontend import args
from frontend import flag_spec
from mycpp.mylib import print_stderr

from typing import List

SPEC = flag_spec.FlagSpec('readlink')
SPEC.ShortFlag('-f')


def main(argv):
  # type: (List[str]) -> int
  arg_r = args.Reader(argv)
  arg_r.Next()  # skip argv[0]
  arg = args.Parse(SPEC, arg_r)

  if not arg.f:
    print_stderr("readlink: -f must be passed")
    return 1
  for path in arg_r.Rest():
    res = libc.realpath(path)
    if res is None:
      return 1
    print(res)
  return 0
