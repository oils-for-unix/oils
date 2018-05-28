#!/usr/bin/env bash
#
# Constructs borrowed from ksh.  Hm I didn't realize zsh also implements these!
# mksh implements most too.

### C-style for loop
n=10
for ((a=1; a <= n ; a++))  # Double parentheses, and naked 'n'
do
  if test $a = 3; then
    continue
  fi
  if test $a = 6; then
    break
  fi
  echo $a
done  # A construct borrowed from ksh93.
## status: 0
## STDOUT:
1
2
4
5
## N-I mksh status: 1
## N-I mksh stdout-json: ""

### For loop with and without semicolon
for ((a=1; a <= 3; a++)); do
  echo $a
done  # A construct borrowed from ksh93.
for ((a=1; a <= 3; a++)) do
  echo $a
done  # A construct borrowed from ksh93.
## status: 0
## STDOUT:
1
2
3
1
2
3
## N-I mksh status: 1
## N-I mksh stdout-json: ""

### For loop with empty head
a=1
for ((;;)); do
  if test $a = 4; then
    break
  fi
  echo $((a++))
done  # A construct borrowed from ksh93.
## status: 0
## STDOUT:
1
2
3
## N-I mksh status: 1
## N-I mksh stdout-json: ""
