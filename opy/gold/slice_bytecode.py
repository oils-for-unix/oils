#!/usr/bin/env python2
"""
slice_bytecode.py
"""

def f():
  stack = [1, 2]
  del stack[:] 
  #stack[:] = [3]
  print(stack)

f()

