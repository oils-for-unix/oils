#!/usr/bin/env python2
"""
invalid_else.py
"""
from __future__ import print_function


def f():
  # type: () -> None

  # Duplicate to see if we can get THREE errors out of mycpp

  try:
    print('hi')
  except IOError:
    pass
  else:
    print('else')

  try:
    print('hi')
  except IOError:
    pass
  else:
    print('else')

def run_tests():
  # type: () -> None

  f()

  try:
    print('hi')
  except IOError:
    pass
  else:
    print('else')
