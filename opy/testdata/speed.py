#!/usr/bin/env python2
def do_sum(n):
  sum = 0
  for i in xrange(n):
    sum += i
  print(sum)

if __name__ == '__main__':
  import sys
  n = int(sys.argv[1])
  do_sum(n)

