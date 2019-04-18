#!/usr/bin/python
"""
switch2.py

Switch without a context manager.  I think switch1 is better.
"""
from __future__ import print_function

import sys

class Switch2(object):
  def __init__(self, value):
    # type: (int) -> None
    self.value = value

  def __iter__(self):
    # type: () -> Iterator[Callable[[Switch2, *Any], bool]]
    yield self.match

  def match(self, *values):
    # type: (*Any) -> bool
    if not values:  # default value
      return True
    return self.value in values


def Other():
  # type: () -> None

  x = 3
  # But this style is probably easier to translate with the MyPy AST
  # And it has the 'break'.

  for case in Switch2(x):
    if case(0):
      print('zero')
      break

    if case(1, 2):
      print('one or two')
      break

    if case(3, 4):
      print('three or four')
      break

    if case():
      print('default')
      break


def main(argv):
  Other()


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
