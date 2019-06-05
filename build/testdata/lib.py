"""
lib.py
"""
from __future__ import print_function

import sys

print('Hello from lib.py', file=sys.stderr)

def Crash():
  raise RuntimeError('oops')

