#!/bin/bash

### (( )) result
(( 1 )) && echo True
(( 0 )) || echo False
# stdout-json: "True\nFalse\n"

### negative number is true
(( -1 )) && echo True
# stdout: True

### (( )) in if statement
if (( 3 > 2)); then
  echo True
fi
# stdout: True

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

### (( )) with error
(( a = 0 )) || echo false
(( b = 1 )) && echo true
(( c = -1 )) && echo true
echo $((a + b + c))
# stdout-json: "false\ntrue\ntrue\n0\n"
