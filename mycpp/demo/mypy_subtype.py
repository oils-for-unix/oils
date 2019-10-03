#!/usr/bin/env python2
"""
Example of MyPy's ability to downcast a var under the same name in a functino.

Our ASDL code gen will rely on this.
"""
from __future__ import print_function

import sys

class Foo(object):
  def __init__(self):
    # type: () -> None
    self.a = 2

class Bar(Foo):
  b = 1
  def __init__(self):
    # type: () -> None
    self.a = 1

class Baz(Foo):
  def __init__(self):
    # type: () -> None
    self.a = 3


from typing import cast

def f(obj, i):
  # type: (Foo, int) -> None
  if i > 5:
    obj = cast(Bar, obj)
    print(obj.b)
  else:
    obj = cast(Baz, obj)
    print(obj.a)


def main():
  # type: () -> None
  f(Bar(), 5)
  print('Hello from m.py')


if __name__ == '__main__':
  try:
    main()
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
