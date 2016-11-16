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

### let
# NOTE: no spaces are allowed.  How is this tokenized?
let x=1
let y=x+2
let z=y*3  # zsh treats this as a glob; bash doesn't
let z2='y*3'  # both are OK with this
echo $x $y $z $z2
# stdout: 1 3 9 9
# OK zsh stdout-json: ""

### let with ()
let x=( 1 )
let y=( x + 2 )
let z=( y * 3 )
echo $x $y $z
# stdout: 1 3 9
# N-I mksh/zsh stdout-json: ""

### (( ))
# What is the difference with this and let?  One difference: spaces are allowed.
(( x = 1 ))
(( y = x + 2 ))
echo $x $y
# stdout: 1 3

### (( )) with arrays
a=(4 5 6)
(( sum = a[0] + a[1] + a[2] ))
echo $sum
# stdout: 15
# OK zsh stdout: 9

### if with (( ))
n=5
if (( 1 <= n && n <= 5 )); then
  echo 'in range'
fi
if (( 3 <= n && n <= 4 )); then
  echo 'in range'
else
  echo 'NOT in range'
fi
# stdout-json: "in range\nNOT in range\n"


### (( )) with error
(( a = 0 )) || echo false
(( b = 1 )) && echo true
(( c = -1 )) && echo true
echo $((a + b + c))
# stdout-json: "false\ntrue\ntrue\n0\n"
