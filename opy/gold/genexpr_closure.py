#!/usr/bin/python
"""
genexpr_closure.py
"""
def main(argv):
  return all(c in ('a', 'b') for c in argv[1:])

  # NO LOAD_CLOSURE in this case.
  #return all([c in ('a', 'b') for c in argv[1:]])
