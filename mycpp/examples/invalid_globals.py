#!/usr/bin/env python2
"""
invalid_types.py
"""
from __future__ import print_function

import os

from mycpp.mylib import log

from typing import List


class Foo(object):
  def __init__(self, x):
    # type: (int) -> None
    self.x = x

a = Foo(1)
b = Foo(2)


