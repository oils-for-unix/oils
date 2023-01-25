#!/usr/bin/env python2
"""
invalid_else.py
"""
from __future__ import print_function


def run_tests():
  # type: () -> None

  try:
    print('hi')
  except IOError:
    pass
  else:
    print('else')
