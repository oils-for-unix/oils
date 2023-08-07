#!/usr/bin/env python2
"""
ref_check.py: Check Links
"""
from __future__ import print_function

import json
import sys


def PrintTree(node, f, indent=0):
  """
  Print DocNode tree in make_help.py
  """
  print('%s%s' % (indent * '  ', node.name), file=f)
  for ch in node.children:
    PrintTree(ch, f, indent+1)


def Check(index_debug_info, chap_tree):

  from pprint import pprint
  pprint(index_debug_info)

  PrintTree(chap_tree, sys.stdout)

# vim: sw=2
