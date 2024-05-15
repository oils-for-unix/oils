#!/usr/bin/env python2
"""
invalid_python.py
"""
from __future__ import print_function

import sys

from typing import List, Any, Iterator


def visit_star(x):
  # type: (Any) -> None
  pass


def f():
  # type: () -> Iterator[int]
  yield 42


class Base:
  pass

class Derived:
  def __init__(self):
    # type: () -> None

    #  Hm not hitting this error
    super(self)


def main():
  # type: () -> None

  # Not handled
  print(u'unicode')

  # This is accepted -- as StrExpr?
  print(b'bytes')

  mycomplex = 3j

  myset = {1, 2}


  mylist = ['hi']
  # This is somehow accepted?  Not StarExpr?
  visit_star(*mylist)
