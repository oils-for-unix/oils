"""
plugin.py - test Python 3 plugin for uftrace
"""

import collections
import os
import sys


def log(msg, *args):
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)


def uftrace_begin(ctx):
  log('script begin %s', ctx)


def uftrace_entry(ctx):
  log('function entry %s', ctx)


def uftrace_exit(ctx):
  log('function exit %s', ctx)


def uftrace_end(ctx):
  log('script end %s', ctx)
