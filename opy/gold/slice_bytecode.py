#!/usr/bin/python
"""
slice_bytecode.py
"""

def f():
  stack = [1, 2]
  del stack[:] 
  #stack[:] = [3]
  print(stack)

f()

