#!/usr/bin/env python2
"""
genexpr_nested.py
"""
from __future__ import print_function

x_ = [1,2,3]
y_ = [4,5,6]

g = ((x,y) for x in x_ for y in y_)
print(list(g))
