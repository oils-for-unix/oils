#!/usr/bin/env bash

#### (( )) result
(( 1 )) && echo True
(( 0 )) || echo False
## stdout-json: "True\nFalse\n"

#### negative number is true
(( -1 )) && echo True
## stdout: True

#### (( )) in if statement
if (( 3 > 2)); then
  echo True
fi
## stdout: True

#### (( ))
# What is the difference with this and let?  One difference: spaces are allowed.
(( x = 1 ))
(( y = x + 2 ))
echo $x $y
## stdout: 1 3

#### (( )) with arrays
a=(4 5 6)
(( sum = a[0] + a[1] + a[2] ))
echo $sum
## stdout: 15
## OK zsh stdout: 9

#### (( )) with error
(( a = 0 )) || echo false
(( b = 1 )) && echo true
(( c = -1 )) && echo true
echo $((a + b + c))
## STDOUT:
false
true
true
0
## END


#### bash and mksh: V in (( a[K] = V )) gets coerced to integer 
shopt -u strict_arith || true
K=key
V=value
typeset -a a
(( a[K] = V ))

# not there!
echo a[\"key\"]=${a[$K]}

echo keys = ${!a[@]}
echo values = ${a[@]}
## STDOUT:
a["key"]=0
keys = 0
values = 0
## END
## N-I zsh status: 1
## N-I zsh stdout-json: ""

#### bash: K in (( A[K] = V )) is a constant string
K=5
V=42
typeset -A A
(( A[K] = V ))

echo A["5"]=${A["5"]}
echo keys = ${!A[@]}
echo values = ${A[@]}
## STDOUT:
A[5]=
keys = K
values = 42
## END
## OK osh status: 1
## OK osh stdout-json: ""
## N-I zsh status: 1
## N-I zsh stdout-json: ""
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### BUG: (( V = A[K] )) doesn't retrieve the right value
typeset -A A
K=5
V=42
A["$K"]=$V
A["K"]=oops
A[K]=oops2

# We don't neither 42 nor "oops".  Bad!
(( V = A[K] ))

echo V=$V
## status: 1
## stdout-json: ""
## BUG bash/zsh status: 0
## BUG bash/zsh STDOUT:
V=0
## END

#### bash: V in (( A["K"] = V )) gets coerced to integer
shopt -u strict_arith || true
K=key
V=value
typeset -A A || exit 1
(( A["K"] = V ))

# not there!
echo A[\"key\"]=${A[$K]}

echo keys = ${!A[@]}
echo values = ${A[@]}
## STDOUT:
A["key"]=
keys = K
values = 0
## END
## N-I zsh stdout-json: ""
## N-I zsh status: 1
## N-I mksh stdout-json: ""
## N-I mksh status: 1

#### literal strings not properly supported in ( ))
declare -A A
A['x']=x
(( x = A['x'] ))
(( A['y'] = 'y' ))  # y is a variable, gets coerced to 0
echo $x ${A['y']}
## status: 1
## stdout-json: ""

# bash behavior is very confusing
## BUG bash status: 0
## BUG bash STDOUT:
0 0
## END
## BUG zsh/mksh status: 0
## N-I zsh/mksh STDOUT:
0
## END

#### (( )) with redirect
(( a = $(stdout_stderr.py 42) + 10 )) 2>$TMP/x.txt
echo $a
echo --
cat $TMP/x.txt
## STDOUT:
52
--
STDERR
## END

#### Can't make assign whole array to var (( b = a ))
a=(4 5 6)
(( b = a ))
echo "${a[@]}"
echo "${b[@]}"
## status: 1
## stdout-json: ""
## BUG bash/mksh status: 0
## BUG bash/mksh STDOUT:
4 5 6
4
## END
## BUG zsh status: 0
## BUG zsh STDOUT:
4 5 6

## END
