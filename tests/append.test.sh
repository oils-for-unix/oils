#!/bin/bash

### Append string to string
s='abc'
s+=d
echo $s
# stdout: abcd

### Append array to array
a=(x y )
a+=(t 'u v')
argv.py "${a[@]}"
# stdout: ['x', 'y', 't', 'u v']

### Append array to string should be an error
s='abc'
s+=(d e f)
echo $s
# BUG bash/mksh stdout: abc
# BUG bash/mksh status: 0
# status: 1

### Append string to array should be disallowed
# They treat this as implicit index 0.  We disallow this on the LHS, so we will
# also disallow it on the RHS.
a=(x y )
a+=z
argv.py "${a[@]}"
# OK bash/mksh stdout: ['xz', 'y']
# OK bash/mksh status: 0
# status: 1

### Append string to array element
# They treat this as implicit index 0.  We disallow this on the LHS, so we will
# also disallow it on the RHS.
a=(x y )
a[1]+=z
argv.py "${a[@]}"
# stdout: ['x', 'yz']
# status: 0

### Append to last element
# Works in bash, but not mksh.  It seems like bash is doing the right thing.
# a[-1] is allowed on the LHS.  mksh doesn't have negative indexing?
a=(1 '2 3')
a[-1]+=' 4'
argv.py "${a[@]}"
# stdout: ['1', '2 3 4']
# BUG mksh stdout: ['1', '2 3', ' 4']

### Try to append list to element
# bash - cannot assign list to array number
# mksh - a[-1]+: is not an identifier
a=(1 '2 3')
a[-1]+=(4 5)
# status: 1

### Strings have value semantics, not reference semantics
s1='abc'
s2=$s1
s1+='d'
echo $s1 $s2
# stdout: abcd abc
