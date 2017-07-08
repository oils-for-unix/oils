#!/usr/bin/env bash
#
# Arrays decay upon assignment (without splicing) and equality.  This will not
# be true in Oil -- arrays will be first class.

### Assignment Causes Array Decay
set -- x y z
#argv "[$@]"  # NOT DECAYED here.
var="[$@]"
argv.py "$var"
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

### Assign to array index without initialization
a[5]=5
a[6]=6
echo "${a[@]}" ${#a[@]}
# stdout: 5 6 2

### a[40] grows array
a=(1 2 3)
a[1]=5
a[40]=30  # out of order
a[10]=20
echo "${a[@]}" "${#a[@]}"  # length is 1
# stdout: 1 5 3 20 30 5

### array decays to string when comparing with [[ a = b ]]
a=('1 2' '3 4')
s='1 2 3 4'  # length 2, length 4
echo ${#a[@]} ${#s}
[[ "${a[@]}" = "$s" ]] && echo EQUAL
# stdout-json: "2 7\nEQUAL\n"

### Increment array variables
a=(1 2)
(( a++ ))  # doesn't make sense
echo "${a[@]}"
# stdout: 2 2

