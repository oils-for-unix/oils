#!/usr/bin/env python2
"""util.py."""
from __future__ import print_function

import sys

# Note: from typing import Any causes ImportError when PYTHONPATH is not .:vendor
# So we import from vendor.typing which is a little inconsistent
#from vendor.typing import Any
from typing import Any


def log(msg, *args):
    # type: (str, Any) -> None
    if args:
        msg = msg % args
    print(msg, file=sys.stderr)
