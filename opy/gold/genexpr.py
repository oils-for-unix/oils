#!/usr/bin/env python2
from __future__ import print_function
"""
Test for generator expressions.
"""

def MakeLookup(p):
  #return dict([(pat, tok) for _, pat, tok in p])
  # Something is broken about how we compile this...
  # Difference in compilation is SETUP_LOOP.  So CPython handle this fine,
  # but bytern doesn't.
  return dict((pat, tok) for _, pat, tok in p)

  # This should be an error but isn't.  Looks like it's not compiled
  # correctly.
  #return list(i for (i, j) in p)

fake_pairs = [
  (False, '-a', 0),
  (False, '-b', 1),
  (False, '-c', 2),
  #(False, '-d', 3),
  #(False, '-e', 4),
  #(False, '-f', 5),
]
#lookup = MakeLookup(id_kind.ID_SPEC.LexerPairs(Kind.BoolUnary))
lookup = MakeLookup(fake_pairs)
print('LOOKUP ***************', len(lookup))
print(lookup)
