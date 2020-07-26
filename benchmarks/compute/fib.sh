#!/bin/sh
#
# POSIX shell script to compute fibonacci many times in a loop.  #
# Shells have similar speeds:
# dash: ~110 ms
# ash: ~290 ms -- the fork is slower!
# zsh: ~290 ms
# mksh: ~380 ms
# bash: ~430 ms
# yash: ~460 ms
#
# Note: all shells use 64 bit integers on 64 bit platforms!  But is that
# justified?  I want shell scripts to be portable!
#
# TODO: detect overflow in OSH.
#
# Note: fib(44) < 2^31, but fib(45) is greater
# Note: fib(544) < 2^63, but fib(545) is greater

iters=${1:-5}  # first argument of every benchmark should be the number of iterations

n=${2:-10}  # fib(n)

i=0
while test $i -lt $iters; do
  j=0

  a=1 b=1

  while test $j -lt $n; do
    # a, b = b, a+b
    tmp=$b
    b=$((a+b))
    a=$tmp

    j=$((j+1))
  done

  echo $b

  i=$((i+1))
done
