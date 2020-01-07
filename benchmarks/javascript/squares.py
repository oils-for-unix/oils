#!/usr/bin/env python2
"""
squares.py
"""
from __future__ import print_function

import sys

n = 1000
x = 10000

def main():
  for i in xrange(n):
    for j in xrange(i, n):
      if i*i + j*j == x:
        print(i, j)


if __name__ == '__main__':
  main()
