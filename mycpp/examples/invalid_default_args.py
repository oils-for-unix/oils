#!/usr/bin/env python2
"""
invalid_too_many_defaults.py
"""
from __future__ import print_function

from typing import List


def ok_None(x=None):
  # type: (str) -> None
  pass


def ok_bool(x=False):
  # type: (bool) -> None
  pass


def too_many_defaults(x, y=4, z=5):
  # type: (int, int, int) -> None
  pass


# I think we should allow None, bool, and int
def mutable_default(x, y=[]):
  # type: (int, List[int]) -> None
  pass


class TooManyDefaults(object):

  def __init__(self, x, y=42, z=5):
    # type: (int, int, int) -> None
    self.x = x
    self.y = y


class MutableDefault(object):

  def __init__(self, x, y=42, z=[]):
    # type: (int, int, List[int]) -> None
    self.x = x
    self.y = y
