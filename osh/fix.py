#!/usr/bin/python
"""
fix.py -- Do source transformations.  Somewhat like 'go fix'.
"""

import sys


# Should this just take an arena, which has all three things?

def Print(pool, spans, node):
  #print node
  #print(spans)
  for span in spans:
    line = pool.GetLine(span.pool_index)
    piece = line[span.col : span.col + span.length]
    print(repr(piece))



