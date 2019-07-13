#!/bin/bash

#### K and V are variables in (( array[K] = V ))
K=5
V=42
typeset -a array
(( array[K] = V ))

echo array[5]=${array[5]}
echo keys = ${!array[@]}
echo values = ${array[@]}
## STDOUT:
array[5]=42
keys = 5
values = 42
## END

#### when are variables set with 'test -v'
test -v unset
echo unset=$?

typeset -a a
test -v a
echo a=$?

typeset -A A
test -v A
echo A=$?

a[0]=1
A['x']=x

test -v a
echo a=$?

# NOTE: This is a BUG!  A is set
test -v A
echo A=$?

## STDOUT:
unset=1
a=1
A=1
a=0
A=0
## END
## BUG bash STDOUT:
unset=1
a=1
A=1
a=0
A=1
## END
## N-I mksh STDOUT:
unset=2
a=2
A=2
a=2
A=2
## END
