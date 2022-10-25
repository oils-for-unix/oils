#!/usr/bin/env python2
"""
uftrace_allocs.py

Count allocations and show sizes.

TODO:
  Attribute allocations and sizes to Str, List, Dict, Token, etc.
  How do we do that?  We need the call graph relationship
"""
from __future__ import print_function

import collections
import sys

num_allocs = 0

def uftrace_begin(ctx):
  pass

def uftrace_entry(ctx):
  global num_allocs

  func_name = ctx["name"]

  #print(ctx)

  if func_name == 'MarkSweepHeap::Allocate':
    num_bytes = ctx['args'][0]
    print(num_bytes)
    num_allocs += 1



def uftrace_exit(ctx):
  pass


def uftrace_end():
  print('num allocated: %d' % num_allocs, file=sys.stderr)

  #print('zz', file=sys.stderr)
