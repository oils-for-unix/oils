#!/usr/bin/env python2
"""util.py."""
from __future__ import print_function

import sys

# many tools import this, causes ImportError
# the oilshell.org/ repo also imports this
#from typing import Any


def log(msg, *args):
    # disabled type: (str, Any) -> None
    if args:
        msg = msg % args
    print(msg, file=sys.stderr)
