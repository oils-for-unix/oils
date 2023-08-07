#!/usr/bin/env python2
"""
ref_check.py: Check Links
"""
from __future__ import print_function

import json
import sys

def main(argv):
  for path in argv[1:]:
    print(path)
    with open(path) as f:
      d = json.load(f)
      print(d)


if __name__ == '__main__':
  main(sys.argv)


# vim: sw=2
