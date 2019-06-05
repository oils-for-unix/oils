from __future__ import print_function
"""
readlink.py - Minimal implementation of readlink -f, e.g. for OS X.
"""

import libc
from frontend import args
from core import ui

SPEC = args.BuiltinFlags()
SPEC.ShortFlag('-f')


def main(argv):
  arg, i = SPEC.ParseArgv(argv)
  if not arg.f:
    ui.Stderr("readlink: -f must be passed")
    return 1
  for path in argv[i:]:
    res = libc.realpath(path)
    if res is None:
      return 1
    print(res)
  return 0
