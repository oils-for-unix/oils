#!/usr/bin/python
from __future__ import print_function
"""
callgraph_demo.py
"""

import sys

from opy import callgraph

_private = '_PRIVATE'
private = 'PRIVATE'


def f():
  sys.settrace(sys.settrace)  # Try passing a type to a type.


def h():
  import dis
  dis.dis(f)

  from core import util
  out = []
  seen = set()
  #_Walk(util.log, util, out)
  callgraph._Walk(util.ShowAppVersion, util, seen, out)

  #_Walk(util.log, sys.modules['core.util'], out)
  print('---')
  for o in out:
    print(o)


def g(argv):
  print(dir(sys))

  g()

  print(private)
  print(_private)


def main(argv):
  callgraph.Walk(g, sys.modules)

  h()


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print >>sys.stderr, 'FATAL: %s' % e
    sys.exit(1)
