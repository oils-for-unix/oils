#!/usr/bin/env python2
"""
invalid_format_args.py
"""
from __future__ import print_function


def run_tests():
  # type: () -> None

  # MyPy catches this: too many args
  s = '%s %%' % ('x', 42)

  # Too few args
  s = '%s %d' % 'x'
