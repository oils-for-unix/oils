#!/usr/bin/env python2
from __future__ import print_function
"""
Simpler test for generator expressions.
"""

def MakeLookup(p):
  return list(i for i in p)

print(MakeLookup([66]))
print(MakeLookup([1,2]))

nums = [4, 5, 6]

g1 = (x for x in range(3))
g2 = (x for x in [2,3,4])
g3 = (x for x in nums) 

print(list(g1))
print(list(g2))
print(list(g3))
