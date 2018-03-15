#!/usr/bin/python
from __future__ import print_function
"""
callgraph_demo.py
"""

import sys

_private = '_PRIVATE'
private = 'PRIVATE'


def g():
  sys.settrace(sys.settrace)  # Try passing a type to a type.


def main(argv):
  print(dir(sys))

  g()

  print(private)
  print(_private)


if __name__ == '__main__':
  import dis
  dis.dis(g)

  if 1:
    from opy import callgraph
    callgraph.Walk(main, sys.modules)
  else:
    try:
      main(sys.argv)
    except RuntimeError as e:
      print >>sys.stderr, 'FATAL: %s' % e
      sys.exit(1)
