#!/bin/bash
#
# Extended assignment language, e.g. typeset, declare, arrays, etc.
# Things that dash doesn't support.

#### local -a
# nixpkgs setup.sh uses this (issue #26)
f() {
  local -a array=(x y z)
  argv.py "${array[@]}"
}
f
## stdout: ['x', 'y', 'z']
## N-I mksh stdout-json: ""
## N-I mksh status: 1

#### declare -a
# nixpkgs setup.sh uses this (issue #26)
declare -a array=(x y z)
argv.py "${array[@]}"
## stdout: ['x', 'y', 'z']
## N-I mksh stdout-json: ""
## N-I mksh status: 1

#### indexed LHS with spaces (not allowed in OSH)
a[1 * 1]=x a[ 1 + 2 ]=z
echo status=$?
argv.py "${a[@]}"
## STDOUT:
status=0
['x', 'z']
## END
## N-I osh STDOUT:
status=127
[]
## END

#### declare -f exit code indicates function existence
func2=x  # var names are NOT found
declare -f myfunc func2
echo $?

myfunc() { echo myfunc; }
# This prints the source code.
declare -f myfunc func2 > /dev/null
echo $?

func2() { echo func2; }
declare -f myfunc func2 > /dev/null
echo $?
## STDOUT:
1
1
0
## END
## N-I mksh STDOUT:
127
127
127
## END

#### declare -F prints function names
add () { expr 4 + 4; }
div () { expr 6 / 2; }
ek () { echo hello; }
__ec () { echo hi; }
_ab () { expr 10 % 3; }

declare -F
## STDOUT:
declare -f __ec
declare -f _ab
declare -f add
declare -f div
declare -f ek
## END
## N-I mksh stdout-json: ""
## N-I mksh status: 127

#### declare -p 
var1() { echo func; }  # function names are NOT found.
declare -p var1 var2 >/dev/null
echo $?

var1=x
declare -p var1 var2 >/dev/null
echo $?

var2=y
declare -p var1 var2 >/dev/null
echo $?
## STDOUT:
1
1
0
## N-I mksh STDOUT:
127
127
127
## END

#### typeset -f 
# mksh implement typeset but not declare
typeset  -f myfunc func2
echo $?

myfunc() { echo myfunc; }
# This prints the source code.
typeset  -f myfunc func2 > /dev/null
echo $?

func2() { echo func2; }
typeset  -f myfunc func2 > /dev/null
echo $?
## STDOUT:
1
1
0
## END

#### typeset -p 
var1() { echo func; }  # function names are NOT found.
typeset -p var1 var2 >/dev/null
echo $?

var1=x
typeset -p var1 var2 >/dev/null
echo $?

var2=y
typeset -p var1 var2 >/dev/null
echo $?
## STDOUT:
1
1
0
## BUG mksh STDOUT:
# mksh doesn't respect exit codes
0
0
0
## END

#### typeset -r makes a string readonly
typeset -r s1='12'
typeset -r s2='34'

s1='c'
echo status=$?
s2='d'
echo status=$?

s1+='e'
echo status=$?
s2+='f'
echo status=$?

unset s1
echo status=$?
unset s2
echo status=$?

## status: 1
## stdout-json: ""
## OK mksh status: 2
## OK bash status: 0
## OK bash STDOUT:
status=1
status=1
status=1
status=1
status=1
status=1
## END

#### typeset -ar makes it readonly
typeset -a -r array1=(1 2)
typeset -ar array2=(3 4)

array1=('c')
echo status=$?
array2=('d')
echo status=$?

array1+=('e')
echo status=$?
array2+=('f')
echo status=$?

unset array1
echo status=$?
unset array2
echo status=$?

## status: 1
## stdout-json: ""
## OK bash status: 0
## OK bash STDOUT:
status=1
status=1
status=1
status=1
status=1
status=1
## END
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### typeset -x makes it exported
typeset -rx PYTHONPATH=lib/
printenv.py PYTHONPATH
## STDOUT:
lib/
## END

#### Multiple assignments / array assignments on a line
a=1 b[0+0]=2 c=3
echo $a ${b[@]} $c
## stdout: 1 2 3

#### Env bindings shouldn't contain array assignments
a=1 b[0]=2 c=3 printenv.py a b c
## status: 2
## stdout-json: ""
## OK bash STDOUT:
1
None
3
## END
## OK bash status: 0
## BUG mksh STDOUT:
1
2
3
## END
## OK mksh status: 0

#### syntax error in array assignment
a=x b[0+]=y c=z
echo $a $b $c
## status: 2
## stdout-json: ""
## BUG bash stdout: x
## BUG bash status: 0
## OK mksh stdout-json: ""
## OK mksh status: 1

#### declare -g (bash-specific; bash-completion uses it)
f() {
  declare -g G=42
  declare L=99

  declare -Ag dict
  dict["foo"]=bar

  declare -A localdict
  localdict["spam"]=Eggs

  # For bash-completion
  eval 'declare -Ag ev'
  ev["ev1"]=ev2
}
f
argv.py "$G" "$L"
argv.py "${dict["foo"]}" "${localdict["spam"]}"
argv.py "${ev["ev1"]}"
## STDOUT:
['42', '']
['bar', '']
['ev2']
## END
## N-I mksh STDOUT:
['', '']
## END
## N-I mksh status: 1

#### myvar=typeset (another form of dynamic assignment)
myvar=typeset
x='a b'
$myvar x=$x
echo $x
## STDOUT:
a
## END
## OK osh STDOUT:
a b
## END

#### dynamic array parsing is not allowed
code='x=(1 2 3)'
typeset -a "$code"  # note: -a flag is required
echo status=$?
argv.py "$x"
## STDOUT:
status=2
['']
## END
## OK mksh STDOUT:
status=0
['(1 2 3)']
## END
# bash allows it
## OK bash STDOUT:
status=0
['1']
## END

#### dynamic flag in array in assign builtin
typeset b
b=(unused1 unused2)  # this works in mksh

a=(x 'foo=F' 'bar=B')
typeset -"${a[@]}"
echo foo=$foo
echo bar=$bar
printenv.py foo
printenv.py bar

# syntax error in mksh!  But works in bash and zsh.
#typeset -"${a[@]}" b=(spam eggs)
#echo "length of b = ${#b[@]}"
#echo "b[0]=${b[0]}"
#echo "b[1]=${b[1]}"

## STDOUT:
foo=F
bar=B
F
B
## END

#### typeset +x
export e=E
printenv.py e
typeset +x e=E2
printenv.py e  # no longer exported
## STDOUT:
E
None
## END

#### typeset +r removes read-only attribute (TODO: documented in bash to do nothing)
readonly r=r1
echo r=$r

# clear the readonly flag.  Why is this accepted in bash, but doesn't do
# anything?
typeset +r r=r2 
echo r=$r

r=r3
echo r=$r

## status: 0
## STDOUT:
r=r1
r=r2
r=r3
## END

# mksh doesn't allow you to unset
## OK mksh status: 2
## OK mksh STDOUT:
r=r1
## END

# bash doesn't allow you to unset
## OK bash status: 0
## OK bash STDOUT:
r=r1
r=r1
r=r1
## END
