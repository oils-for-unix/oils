#!/usr/bin/env python
from __future__ import print_function
"""
opy_.py
"""

import os
import sys

this_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(os.path.join(this_dir, '..'))

from core import args

from opy.util_opy import log
from opy import opy_main


# TODO: move to quick ref?
_OPY_USAGE = 'Usage: opy_ MAIN [OPTION]... [ARG]...'


# TODO: Make this more consistent with bin/oil.py.

def main(argv):
  try:
    opy_main.OpyMain(argv[1:])
  except args.UsageError as e:
    print(_OPY_USAGE, file=sys.stderr)
    print(str(e), file=sys.stderr)
    sys.exit(2)
  except RuntimeError as e:
    log('FATAL: %s', e)
    sys.exit(1)


if __name__ == '__main__':
  main(sys.argv)
