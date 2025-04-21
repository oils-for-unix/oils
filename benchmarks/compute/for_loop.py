#!/usr/bin/env python2

import sys

n = int(sys.argv[1])
sum = 0
for i in xrange(n):
    sum += i
#print(f"sum = {sum}")
print("n = %d" % n)
print("sum = %d" % sum)
