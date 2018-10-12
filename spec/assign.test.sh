#!/usr/bin/env bash

#### Env value doesn't persist
FOO=foo printenv.py FOO
echo [$FOO]
## STDOUT:
foo
[]
## END

#### Env value with equals
FOO=foo=foo printenv.py FOO
## stdout: foo=foo

#### Env binding can use preceding bindings, but not subsequent ones
# This means that for ASSIGNMENT_WORD, on the RHS you invoke the parser again!
# Could be any kind of quoted string.
FOO="foo" BAR="[$FOO][$BAZ]" BAZ=baz printenv.py FOO BAR BAZ
## STDOUT:
foo
[foo][]
baz
## BUG mksh STDOUT:
foo
[][]
baz
## END

#### Env value with two quotes
FOO='foo'"adjacent" printenv.py FOO
## stdout: fooadjacent

#### Env value with escaped <
FOO=foo\<foo printenv.py FOO
## stdout: foo<foo

#### FOO=foo echo [foo]
FOO=foo echo "[$foo]"
## stdout: []

#### FOO=foo func
func() {
  echo "[$FOO]"
}
FOO=foo func
## stdout: [foo]

#### Multiple temporary envs on the stack
g() {
  echo "$F" "$G1" "$G2"
  echo '--- g() ---'
  P=p printenv.py F G1 G2 A P
}
f() {
  # NOTE: G1 doesn't pick up binding f, but G2 picks up a.
  # I don't quite understand why this is, but bash and OSH agree!
  G1=[$f] G2=[$a] g
  echo '--- f() ---'
  printenv.py F G1 G2 A P
}
a=A
F=f f
## STDOUT:
f [] [A]
--- g() ---
f
[]
[A]
None
p
--- f() ---
f
None
None
None
None
## END
## OK mksh STDOUT:
# G1 and G2 somehow persist.  I think that is a bug.  They should be local to
# the G call.
f [] [A]
--- g() ---
f
[]
[A]
None
p
--- f() ---
f
[]
[A]
None
None
## END
## BUG dash STDOUT:
# dash sets even less stuff.  Doesn't appear correct.
f [] [A]
--- g() ---
None
None
None
None
p
--- f() ---
None
None
None
None
None
## END

#### Escaped = in command name
# foo=bar is in the 'spec/bin' dir.
foo\=bar
## stdout: HI

#### Env binding not allowed before compound command
# bash gives exit code 2 for syntax error, because of 'do'.
# dash gives 0 because there is stuff after for?  Should really give an error.
# mksh gives acceptable error of 1.
FOO=bar for i in a b; do printenv.py $FOO; done
## BUG dash status: 0
## OK  mksh status: 1
## status: 2

#### Trying to run keyword 'for'
FOO=bar for
## status: 127

#### Empty env binding
EMPTY= printenv.py EMPTY
## stdout:

#### Assignment doesn't do word splitting
words='one two'
a=$words
argv.py "$a"
## stdout: ['one two']

#### Assignment doesn't do glob expansion
touch _tmp/z.Z _tmp/zz.Z
a=_tmp/*.Z
argv.py "$a"
## stdout: ['_tmp/*.Z']

#### Env binding in readonly/declare disallowed
# I'm disallowing this in the oil shell, because it doesn't work in bash!
# (v=None vs v=foo)
# assert status 2 for parse error, but allow stdout v=None/status 0 for
# existing implementations.
FOO=foo readonly v=$(printenv.py FOO)
echo "v=$v"
## OK bash/dash/mksh stdout: v=None
## OK bash/dash/mksh status: 0
## status: 2

#### local -a
# nixpkgs setup.sh uses this (issue #26)
f() {
  local -a array=(x y z)
  argv.py "${array[@]}"
}
f
## stdout: ['x', 'y', 'z']
## N-I dash stdout-json: ""
## N-I dash status: 2
## N-I mksh stdout-json: ""
## N-I mksh status: 1

#### declare -a
# nixpkgs setup.sh uses this (issue #26)
declare -a array=(x y z)
argv.py "${array[@]}"
## stdout: ['x', 'y', 'z']
## N-I dash stdout-json: ""
## N-I dash status: 2
## N-I mksh stdout-json: ""
## N-I mksh status: 1

#### typeset -a a[1]=a a[3]=c
# declare works the same way in bash, but not mksh.
# spaces are NOT allowed here.
typeset -a a[1*1]=x a[1+2]=z
argv.py "${a[@]}"
## stdout: ['x', 'z']
## N-I dash stdout-json: ""
## N-I dash status: 2

#### indexed LHS without spaces is allowed
a[1 * 1]=x a[ 1 + 2 ]=z
argv.py "${a[@]}"
## stdout: ['x', 'z']
## N-I dash stdout-json: ""
## N-I dash status: 2

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
## N-I dash/mksh STDOUT:
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
## N-I dash/mksh stdout-json: ""
## N-I dash/mksh status: 127

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
## N-I dash/mksh STDOUT:
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
## N-I dash STDOUT:
127
127
127
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
## N-I dash STDOUT:
127
127
127
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
## OK dash status: 0
## N-I dash STDOUT:
status=0
status=0
status=127
status=127
status=0
status=0
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
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I mksh status: 1
## N-I mksh stdout-json: ""

#### typeset -x makes it exported
typeset -rx PYTHONPATH=lib/
printenv.py PYTHONPATH
## STDOUT:
lib/
## END
## N-I dash stdout: None

#### Multiple assignments / array assignments on a line
a=1 b[0+0]=2 c=3
echo $a $b $c
## stdout: 1 2 3
## N-I dash stdout:

#### assignments / array assignments not interpreted after 'echo'
a=1 echo b[0]=2 c=3
## stdout: b[0]=2 c=3

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
## N-I dash stdout-json: ""
## N-I dash status: 127

#### syntax error in array assignment
a=x b[0+]=y c=z
echo $a $b $c
## status: 2
## stdout-json: ""
## BUG bash stdout: x
## BUG bash status: 0
## OK mksh stdout-json: ""
## OK mksh status: 1
## N-I dash stdout:
## N-I dash status: 0

#### dynamic local variables
f() {
  local "$1"  # Only x is assigned here
  echo [$x]
  echo [$a]

  local $1  # x and a are assigned here
  echo [$x]
  echo [$a]
}
f 'x=y a=b'
## STDOUT:
[y a=b]
[]
[y]
[b]
## END

#### 'local x' does not set variable
set -o nounset
f() {
  local x
  echo $x
}
f
## status: 1
## OK dash status: 2

#### 'local -a x' does not set variable
set -o nounset
f() {
  local -a x
  echo $x
}
f
## status: 1
## OK dash status: 2

#### 'local x' and then array assignment
f() {
  local x
  x[3]=foo
  echo ${x[3]}
}
f
## status: 0
## stdout: foo
## N-I dash status: 2
## N-I dash stdout-json: ""

#### 'declare -A' and then dict assignment
set -o strict-arith
declare -A foo
key=bar
foo["$key"]=value
echo ${foo["bar"]}
## status: 0
## stdout: value
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I mksh status: 1
## N-I mksh stdout-json: ""

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
## N-I dash STDOUT:
['', '']

## END
## N-I dash status: 2
## N-I mksh STDOUT:
['', '']

## END
## N-I mksh status: 1

#### declare in an if statement
# bug caught by my feature detection snippet in bash-completion
if ! foo=bar; then
  echo BAD
fi
echo $foo
if ! eval 'spam=eggs'; then
  echo BAD
fi
echo $spam
## STDOUT:
bar
eggs
## END

