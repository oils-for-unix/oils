#!/usr/bin/env python
from __future__ import print_function
"""
Simpler test for generator expressions.
"""

def MakeLookup(p):
  return list(i for i in p)
  #return list([i for i in p])

print(MakeLookup([66]))
# This runs but prints []
#print(MakeLookup([1,2]))
