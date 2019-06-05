#!/usr/bin/env python2
from __future__ import print_function
"""Iterative version of Fibonacci."""

i = 0
n = 10
a = 0
b = 1

while 1:  # Slightly easier to compile than 'while True:'

  # Artifical change to test 'continue'
  if i == 0:
    i = i + 1
    continue

  print(b)

  # NOTE: This would generate BUILD_TUPLE and UNPACK_SEQUENCE bytecodes.
  #a, b = b, a+b

  tmp = a
  a = b
  b = tmp + b

  i = i + 1  # Don't use augmented assignment
  if i == n:
    break

print('Done fib_iterative.py')  # To make sure we implemented 'break' properly
