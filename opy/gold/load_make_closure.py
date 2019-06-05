#!/usr/bin/env python2
"""
load_make_closure.py - A generator expression should not generate the
LOAD_CLOSURE or MAKE_CLOSURE bytecodes.
"""
# Copied from core/braces.py
# It erroneously generaets a closure because of:
# co_freevars:        ('parts_list',)
#
# In CPython that list is empty.
def BraceExpandWords(words):
  parts_list = []
  print(p for p in parts_list if len(p) > 2)
