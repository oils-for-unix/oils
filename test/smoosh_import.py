#!/usr/bin/env python2
"""
import_smoosh.py

Choose between STDOUT and stdout-json assertions.
"""
from __future__ import print_function

import json
import sys


def main(argv):
  stdout_file = argv[1]
  with open(stdout_file) as f:
    expected = f.read()
    
  if expected.endswith('\n'):  # not including empty
    print('## STDOUT:')
    print(expected, end='')
    print('## END')
  else:
    print('## stdout-json: %s' % json.dumps(expected))


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
