#!/usr/bin/python
from __future__ import print_function
"""
readlink.py
"""

import os
import libc
from core import args, util

SPEC = args.BuiltinFlags()
SPEC.ShortFlag('-f')


def main(argv):
  arg, i = SPEC.Parse(argv)
  if not arg.f:
    util.error("-f must be passed")
    return 1
  for arg in argv[i:]:
    res = libc.readlinkf(arg)
    if res == -1:
        return 1
    print(res)
  return 0
