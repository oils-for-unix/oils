#!/usr/bin/env python2
"""
invalid_too_many_defaults.py
"""
from __future__ import print_function

from typing import List, Dict

s = ''
mylist = []  # type: List[int]
d = {}  # type: Dict[int, int]

if s:
    print('string')

if mylist:
    print('List')

if d:
    print('Dict')

b = True if s else False
b = True if mylist else False
b = True if d else False

if not mylist:
    print('List')

other_list = []  # type: List[str]
if not mylist and not other_list:
    print('List')
