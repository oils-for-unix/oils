"""
runtime.py

- Base classes for generated code
- Nodes for pretty printing
"""
from __future__ import print_function

from _devbuild.gen.hnode_asdl import (
    hnode__Record, hnode__Leaf, color_t, color_e
)

from typing import Optional


# Used throughout the "LST" to indicate we don't have location info.
NO_SPID = -1

def NewRecord(node_type):
  # type: (str) -> hnode__Record
  return hnode__Record(
      node_type,
      [],  # fields
      False, '(', ')',  # abbrev, left, right
      []  # unnamed fields
  )


def NewLeaf(s, e_color):
  # type: (Optional[str], color_t) -> hnode__Leaf

  # for repr of MaybeStrArray, which can have 'None'
  if s is None:
    return hnode__Leaf('_', color_e.OtherConst)
  else:
    return hnode__Leaf(s, e_color)


# Constants to avoid 'new Str("T")' in ASDL-generated code
TRUE_STR = 'T'
FALSE_STR = 'F'
