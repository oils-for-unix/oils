#!/usr/bin/env python
"""
Simpler test for generator expressions.
"""

def MakeLookup(p):
  return list(i for i in p)
  #return list([i for i in p])

print(MakeLookup([66]))
# This runs but prints []
#print(MakeLookup([1,2]))
