#!/usr/bin/env python2
"""
yaml2json.py
"""
from __future__ import print_function

import json
import sys

import yaml


def main(argv):
  with open(argv[1]) as f:
    obj = yaml.safe_load(f)

  json.dump(obj, sys.stdout, indent=2)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
