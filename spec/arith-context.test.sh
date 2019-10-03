#!/usr/bin/env bash
#
# Test arithmetic expressions in all their different contexts.

# $(( 1 + 2 ))
# (( a=1+2 ))
# ${a[ 1 + 2 ]}
# ${a : 1+2 : 1+2}
# a[1 + 2]=foo

#### Multiple right brackets inside expression
a=(1 2 3)
echo ${a[a[0]]} ${a[a[a[0]]]}
## stdout: 2 3
## N-I zsh status: 0
## N-I zsh stdout-json: "\n"

#### Slicing of string with constants
s='abcd'
echo ${s:0} ${s:0:4} ${s:1:1}
## stdout: abcd abcd b

#### Slicing of string with variables
s='abcd'
zero=0
one=1
echo ${s:$zero} ${s:$zero:4} ${s:$one:$one}
## stdout: abcd abcd b

#### Array index on LHS of assignment
a=(1 2 3)
zero=0
a[zero+5-4]=X
echo ${a[@]}
## stdout: 1 X 3
## OK zsh stdout: X 2 3

#### Array index on LHS with indices
a=(1 2 3)
a[a[1]]=X
echo ${a[@]}
## stdout: 1 2 X
## OK zsh stdout: X 2 3

#### Slicing of string with expressions
# mksh accepts ${s:0} and ${s:$zero} but not ${s:zero}
# zsh says unrecognized modifier 'z'
s='abcd'
zero=0
echo ${s:zero} ${s:zero+0} ${s:zero+1:zero+1}
## stdout: abcd abcd b
## BUG mksh stdout-json: ""
## BUG mksh status: 1
## BUG zsh stdout-json: ""
## BUG zsh status: 1

#### Ambiguous colon in slice
s='abcd'
echo $(( 0 < 1 ? 2 : 0 ))  # evalutes to 2
echo ${s: 0 < 1 ? 2 : 0 : 1}  # 2:1 -- TRICKY THREE COLONS
## stdout-json: "2\nc\n"
## BUG mksh stdout-json: "2\n"
## BUG mksh status: 1
## BUG zsh stdout-json: "2\n"
## BUG zsh status: 1

#### Triple parens should be disambiguated
# The first paren is part of the math, parens 2 and 3 are a single token ending
# arith sub.
((a=1 + (2*3)))
echo $a $((1 + (2*3)))
## stdout: 7 7

#### Quadruple parens should be disambiguated
((a=1 + (2 * (3+4))))
echo $a $((1 + (2 * (3+4))))
## stdout: 15 15

#### ExprSub $[] happpens to behave the same on simple cases
echo $[1 + 2] "$[3 * 4]"
## stdout: 3 12
## N-I mksh stdout: $[1 + 2] $[3 * 4]
