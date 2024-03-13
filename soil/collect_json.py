#!/usr/bin/env python3
"""
collect_json.py: Dump files and selected environment variables as JSON.
"""
from __future__ import print_function

import glob
import json
import os
import sys


def main(argv):
  d = {}
  metadata_dir = argv[1]

  for path in glob.glob('%s/*.txt' % metadata_dir):
    filename = os.path.basename(path)
    key, _ = os.path.splitext(filename)
    with open(path) as f:
      value = f.read()
    d[key] = value.strip()

  for name in argv[2:]:
    d[name] = os.getenv(name)  # could be None
  json.dump(d, sys.stdout, indent=2)
  print()


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
