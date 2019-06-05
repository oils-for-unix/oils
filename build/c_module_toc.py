#!/usr/bin/env python2
from __future__ import print_function
"""
c_module_toc.py
"""

import glob
import re
import sys


PURE_C_RE = re.compile(r'.*/(.*)module\.c$')
HELPER_C_RE = re.compile(r'.*/(.*)\.c$')


def main(argv):
  # module name -> list of paths to include
  c_module_srcs = {}

  for c_path in glob.glob('Modules/*.c') + glob.glob('Modules/_io/*.c'):
    m = PURE_C_RE.match(c_path)
    if m:
      print(m.group(1), c_path)
      continue

    m = HELPER_C_RE.match(c_path)
    if m:
      name = m.group(1)
      # Special case:
      if name == '_hashopenssl':
        name = '_hashlib'
      print(name, c_path)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
