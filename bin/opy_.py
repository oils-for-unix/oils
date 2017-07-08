#!/usr/bin/env python
"""
opy_.py
"""

import os
import sys

this_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
sys.path.append(os.path.join(this_dir, '..'))

from opy import opy_main

opy_main.main(sys.argv)
