#!/usr/bin/python
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
  out = []
  for w in words:
    if w.tag == word_e.BracedWordTree:
      parts_list = _BraceExpand(w.parts)
      out.extend(ast.CompoundWord(p) for p in parts_list)
    else:
      out.append(w)
  return out
