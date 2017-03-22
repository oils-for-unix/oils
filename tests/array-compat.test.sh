#!/bin/bash
#
# Arrays decay upon assignment (without splicing) and equality.  This will not
# be true in Oil -- arrays will be first class.

### Assignment Causes Array Decay
set -- x y z
#argv "[$@]"  # NOT DECAYED here.
var="[$@]"
argv "$var"
# stdout: ['[x y z]']

### User arrays decay
declare -a a b
a=(x y z)
b="${a[@]}"  # this collapses to a string
c=("${a[@]}")  # this preserves the array
c[1]=YYY  # mutate a copy -- doesn't affect the original
argv.py "${a[@]}" "${b[@]}" "${c[@]}"
# stdout: ['x', 'y', 'z', 'x y z', 'x', 'YYY', 'z']

### $a gives first element of array
a=(1 '2 3')
echo $a
# stdout: 1

