#!/usr/bin/awk -f

BEGIN {
  n = ARGV[1]
  sum = 0
  i = 0
  while (i < n) {
    sum += i
    i++
  }
  print "n = " n
  print "sum = " sum
}
