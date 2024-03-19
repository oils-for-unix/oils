#!/usr/bin/env python2
"""
invalid_global.py
"""
from __future__ import print_function

from mycpp.mylib import log


class C:

    def __init__(self):
        # type: () -> None
        self.i = 42


g1 = C()
g2 = C()
