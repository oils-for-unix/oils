#!/usr/bin/env python2
"""
obj_literals.py
"""
from __future__ import print_function

# Hm in OPy, ALL of these do a bunch of LOAD_CONST, and then BUILD_LIST,
# BUILD_TUPLE, BUILD_SET.  dict is done with BUILD_MAP and STORE_SUBSCR.

# In CPython:

# - the tuple is stored as a whole constant.
# - A STORE_MAP bytecode is used for the dictionary.

# (CPython tested with ../bin/opyc dis gold/obj_literals.pyc, after manually
# importing this file.)

def f():
  mylist = [1, 2, 3]  # 3 LOAD_CONST then BUILD_LIST

  mytuple = ('str', 42)

  f(('a', 3))

  d = {'key': 3}
  myset = {1, 2}
