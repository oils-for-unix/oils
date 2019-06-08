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

#### typeset -a a[1]=a a[3]=c
# declare works the same way in bash, but not mksh.
# spaces are NOT allowed here.
typeset -a a[1*1]=x a[1+2]=z
argv.py "${a[@]}"
## stdout: ['x', 'z']

#### indexed LHS without spaces is allowed
a[1 * 1]=x a[ 1 + 2 ]=z
argv.py "${a[@]}"
## stdout: ['x', 'z']

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
echo $a $b $c
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

