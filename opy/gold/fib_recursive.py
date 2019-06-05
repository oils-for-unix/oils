#!/usr/bin/env python2
from __future__ import print_function
"""Recursive version if Fibonacci."""


def unused():
  """A function that shouldn't be compiled."""
  return 42


def fib(n):
  if n == 0:
    return 1
  elif n == 1:
    return 1
  else:
    return fib(n-1) + fib(n-2)

print(fib(9))


# TODO: Do this later.
if 0:
  def main():
    for i in xrange(9):
      print(fib(i))
    print('Done fib_recursive.py')


  if __name__ == '__main__':
    import os
    if os.getenv('CALLGRAPH') == '1':
      import sys
      from opy import callgraph
      callgraph.Walk(main, sys.modules)
    else:
      main()
