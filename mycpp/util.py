"""
util.py
"""
from __future__ import print_function

import sys

from typing import Any


def log(msg: str, *args: Any) -> None:
  if args:
    msg = msg % args
  print(msg, file=sys.stderr)
