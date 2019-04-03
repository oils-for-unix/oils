#!/usr/bin/python
"""
runtime.py
"""
from __future__ import print_function

import sys
from typing import Any


# C code ignores this!
def log(msg, *args):
  # type: (str, *Any) -> None
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)



