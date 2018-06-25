#!/usr/bin/python
from __future__ import print_function

i = 0
n = 10
a = 0
b = 1

while True:
  print(b)

  # NOTE: This would generate BUILD_TUPLE and UNPACK_SEQUENCE bytecodes.
  #a, b = b, a+b

  tmp = a
  a = b
  b = tmp + b

  i += 1
  if i == n:
    break
