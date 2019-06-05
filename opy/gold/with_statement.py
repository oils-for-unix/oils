#!/usr/bin/env python2
"""
with_statement.py
"""
# Make it local so we use STORE_FAST instead of STORE_NAME, etc.
def f():
  with open('foo.txt') as f:
    contents = f.read()

