#!/usr/bin/env bash
#
# Arrays decay upon assignment (without splicing) and equality.  This will not
# be true in Oil -- arrays will be first class.

#### Assignment Causes Array Decay
set -- x y z
argv.py "[$@]"
var="[$@]"
argv.py "$var"
## STDOUT:
['[x', 'y', 'z]']
['[x y z]']
## END

#### Array Decay with IFS
IFS=x
set -- x y z
var="[$@]"
argv.py "$var"
## stdout: ['[x y z]']

#### User arrays decay
declare -a a b
a=(x y z)
b="${a[@]}"  # this collapses to a string
c=("${a[@]}")  # this preserves the array
c[1]=YYY  # mutate a copy -- doesn't affect the original
argv.py "${a[@]}"
argv.py "${b}"
argv.py "${c[@]}"
## STDOUT:
['x', 'y', 'z']
['x y z']
['x', 'YYY', 'z']
## END

#### $array is not valid in OSH, is ${array[0]} in ksh/bash
a=(1 '2 3')
echo $a
## STDOUT:
1
## END
## OK osh status: 1
## OK osh stdout-json: ""

#### ${array} is not valid in OSH, is ${array[0]} in ksh/bash
a=(1 '2 3')
echo ${a}
## STDOUT:
1
## END
## OK osh status: 1
## OK osh stdout-json: ""

#### Assign to array index without initialization
a[5]=5
a[6]=6
echo "${a[@]}" ${#a[@]}
## stdout: 5 6 2

#### a[40] grows array
a=(1 2 3)
a[1]=5
a[40]=30  # out of order
a[10]=20
echo "${a[@]}" "${#a[@]}"  # length is 1
## stdout: 1 5 3 20 30 5

#### array decays to string when comparing with [[ a = b ]]
a=('1 2' '3 4')
s='1 2 3 4'  # length 2, length 4
echo ${#a[@]} ${#s}
[[ "${a[@]}" = "$s" ]] && echo EQUAL
## STDOUT:
2 7
EQUAL
## END

#### ++ on a whole array increments the first element (disallowed in OSH)
a=(1 10)
(( a++ ))  # doesn't make sense
echo "${a[@]}"
## stdout: 2 10
## OK osh status: 1
## OK osh stdout-json: ""

#### Apply vectorized operations on ${a[*]}
a=('-x-' 'y-y' '-z-')

# This does the prefix stripping FIRST, and then it joins.
argv.py "${a[*]#-}"
## STDOUT:
['x- y-y z-']
## END
## N-I mksh status: 1
## N-I mksh stdout-json: ""
