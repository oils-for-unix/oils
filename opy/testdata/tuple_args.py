#!/usr/bin/env python2
from __future__ import print_function
"""
tuple_args.py: Testing out this little-known feature of Python, which compiler2
suppports.
"""

# Python 3 no longer supports this!
def f(a, (b, c), (d, e, f)):
  print(a, b, c, d, e, f)

if __name__ == '__main__':
  f(1, (2, 3), (4, 5, 6))
