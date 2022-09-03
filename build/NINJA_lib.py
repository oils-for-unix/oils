#!/usr/bin/env python2
"""
NINJA_lib.py
"""
from __future__ import print_function

import os


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def ObjPath(src_path, compiler, variant):
  rel_path, _ = os.path.splitext(src_path)
  return '_build/obj/%s-%s/%s.o' % (compiler, variant, rel_path)
