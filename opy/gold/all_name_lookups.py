#!/usr/bin/env python2
"""
all_name_lookups.py

This program demonstrates all of the following:

  LOAD_FAST   - for optimized locals
  LOAD_NAME   - for class and module namespaces
  LOAD_ATTR   - for the . operator
                uses the descriptor protocol to look up methods!
  LOAD_GLOBAL - when the compiler knows about 'global' ?
              - and when you're at the global scope
  LOAD_CONST  - for looking up in the CodeObject

Note: LOAD_ATTR seems to be very common.

"""
from __future__ import print_function

import class_vs_closure

def myfunc():
  a = 1       # STORE_FAST
  print(a+1)  # LOAD_GLOBAL for print, LOAD_FAST for a

  # LOAD_GLOBAL  for module
  # LOAD_ATTR    for Adder
  # LOAD_CONST   for 42
  # CALL_FUNCTION -- should be INIT_INSTANCE
  obj = class_vs_closure.Adder(42)

  obj.method(5)  # LOAD_FAST and hten LOAD_ATTR for method
                 # CALL_FUNCTION (should be CALL_METHOD)


class F(object):
  def __init__(self, x):
    self.x = 42  # LOAD_FAST for self
                 # STORE_ATTR for self.x = 42

  def method(self):
    print(self.x)
    # LOAD_GLOBAL for print
    # LOAD_FAST for self
    # LOAD_ATTR for x


g = 1
print(g+2)  # LOAD_NAME for print, LOAD_NAME for g too.
