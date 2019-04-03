"""
util.py
"""
from __future__ import print_function

import sys


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)
