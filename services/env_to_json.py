#!/usr/bin/env python2
"""
env_to_json.py: Dump selected environment variables as JSON.
"""
from __future__ import print_function

import json
import os
import sys


def main(argv):
  d = {}
  for name in argv[1:]:
    d[name] = os.getenv(name)  # could be None
  json.dump(d, sys.stdout, indent=2)
  print()


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
