#!/usr/bin/env python2
"""
yaml2json.py

Note: this tool is incorrect!  See 'bug' in yaml2json.sh.

https://john-millikin.com/json-is-not-a-yaml-subset
"""
from __future__ import print_function

import json
import sys

import yaml


def main(argv):
  argv = argv[1:]

  if len(argv) == 0:
    obj = yaml.safe_load(sys.stdin)

  elif len(argv) == 1:
    with open(argv[1]) as f:
      obj = yaml.safe_load(f)

  else:
    raise RuntimeError('Too many args')

  json.dump(obj, sys.stdout, indent=2)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
