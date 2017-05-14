#!/bin/bash
#
# Constructs borrowed from ksh.  Hm I didn't realize zsh also implements these!
# mksh implements most too.

### C-style for loop
n=5
for ((a=1; a <= n ; a++))  # Double parentheses, and naked 'n'
do
  echo $a
done  # A construct borrowed from ksh93.
# stdout-json: "1\n2\n3\n4\n5\n"
# N-I mksh stdout-json: ""

### For loop with and without semicolon
for ((a=1; a <= 3; a++)); do
  echo $a
done  # A construct borrowed from ksh93.
for ((a=1; a <= 3; a++)) do
  echo $a
done  # A construct borrowed from ksh93.
# stdout-json: "1\n2\n3\n1\n2\n3\n"
# N-I mksh stdout-json: ""

