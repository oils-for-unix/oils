#!/usr/bin/env python2
"""
set_comp.py
"""
from __future__ import print_function

s = {x+1 for x in (1,2,3)}
print(s)

d = {x+1: None for x in (1,2,3)}
print(d)

