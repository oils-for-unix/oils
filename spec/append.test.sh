#!/usr/bin/env bash

#### Append string to string
s='abc'
s+=d
echo $s
## stdout: abcd

#### Append array to array
a=(x y )
a+=(t 'u v')
argv.py "${a[@]}"
## stdout: ['x', 'y', 't', 'u v']

#### Append array to string should be an error
s='abc'
s+=(d e f)
echo $s
## BUG bash/mksh stdout: abc
## BUG bash/mksh status: 0
## status: 1

#### Append string to array should be disallowed
# They treat this as implicit index 0.  We disallow this on the LHS, so we will
# also disallow it on the RHS.
a=(x y )
a+=z
argv.py "${a[@]}"
## OK bash/mksh stdout: ['xz', 'y']
## OK bash/mksh status: 0
## status: 1

#### Append string to array element
# They treat this as implicit index 0.  We disallow this on the LHS, so we will
# also disallow it on the RHS.
a=(x y )
a[1]+=z
argv.py "${a[@]}"
## stdout: ['x', 'yz']
## status: 0

#### Append to last element
# Works in bash, but not mksh.  It seems like bash is doing the right thing.
# a[-1] is allowed on the LHS.  mksh doesn't have negative indexing?
a=(1 '2 3')
a[-1]+=' 4'
argv.py "${a[@]}"
## stdout: ['1', '2 3 4']
## BUG mksh stdout: ['1', '2 3', ' 4']

#### Try to append list to element
# bash - runtime error: cannot assign list to array number
# mksh - a[-1]+: is not an identifier
# osh - parse error -- could be better!
a=(1 '2 3')
a[-1]+=(4 5)
argv.py "${a[@]}"
## OK bash STDOUT:
['1', '2 3']
## END
## OK bash status: 0
## N-I mksh stdout-json: ""
## N-I mksh status: 1
## OK stdout-json: ""
## OK osh status: 2

#### Strings have value semantics, not reference semantics
s1='abc'
s2=$s1
s1+='d'
echo $s1 $s2
## stdout: abcd abc

#### Append to nonexistent string
f() {
  local a+=a
  echo $a

  b+=b
  echo $b

  readonly c+=c
  echo $c

  export d+=d
  echo $d

  # Not declared anywhere
  e[1]+=e
  echo ${e[1]}

  # Declare is the same, but mksh doesn't support it
  #declare e+=e
  #echo $e
}
f
## STDOUT:
a
b
c
d
e
## END

# += is invalid on assignment builtins
## OK osh stdout-json: ""
## OK osh status: 1


#### Append to nonexistent array is allowed

## TODO: strict_array could get rid of this?
y+=(c d)
argv.py "${y[@]}"
## STDOUT:
['c', 'd']
## END

#### Append used like env prefix is a parse error
# This should be an error in other shells but it's not.
A=a
A+=a printenv.py A
## status: 2
## BUG bash stdout: aa
## BUG bash status: 0
## BUG mksh stdout: a
## BUG mksh status: 0
