#!/usr/bin/env python2
from __future__ import print_function
"""
Generate C++ strings that can be used by pyutil._ResourceLoader

Used for 

- _devbuild/help/
- stdlib/
"""
import sys


def main(argv):
  #action = argv[1]
  paths = argv[1:]

  f = sys.stdout

  # Invoke with _devbuild/help/* stdlib/*.ysh I guess?

  for rel_path in paths:
    with open(rel_path) as f:
      contents = f.read()

  f.write('''
#include "cpp/embedded_file.h"

TextFile* gEmbeddedFiles = nullptr;
''')


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)


# vim: sw=2
