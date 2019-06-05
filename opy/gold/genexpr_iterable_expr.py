#!/usr/bin/env python2
"""
genexpr_iterable_expr.py
"""
from __future__ import print_function

def f():
  # range is used in THIS scope (the scope of f), not the generator
  # expression's scope.
  return (x for x in range(3))

g = f()
for x in g:
    print(x)
