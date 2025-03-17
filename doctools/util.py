#!/usr/bin/env python2
from __future__ import print_function

import sys

from typing import Any


def log(msg, *args):
    # type: (str, Any) -> None
    if args:
        msg = msg % args
    print(msg, file=sys.stderr)
