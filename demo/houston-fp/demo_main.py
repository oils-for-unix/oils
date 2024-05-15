#!/usr/bin/env python2
from __future__ import print_function
"""
houston-fp demo
"""

import sys

from demo_asdl import Token

from typing import List, cast


def main(argv):
  # type: (List[str]) -> None

  t = Token(3, 4, 5, 'foo')
  print(t)


if __name__ == '__main__':
  try:
    main(sys.argv)
  except RuntimeError as e:
    print('FATAL: %s' % e, file=sys.stderr)
    sys.exit(1)
