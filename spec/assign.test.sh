#!/usr/bin/env bash

### Env value doesn't persist
FOO=foo printenv.py FOO
echo [$FOO]
# STDOUT:
foo
[]
## END

### Env value with equals
FOO=foo=foo printenv.py FOO
## stdout: foo=foo

### Env binding can use preceding bindings, but not subsequent ones
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

### Env value with two quotes
FOO='foo'"adjacent" printenv.py FOO
# stdout: fooadjacent

### Env value with escaped <
FOO=foo\<foo printenv.py FOO
## stdout: foo<foo

### FOO=foo echo [foo]
FOO=foo echo "[$foo]"
## stdout: []

### FOO=foo func
func() {
  echo "[$FOO]"
}
FOO=foo func
## stdout: [foo]

### Multiple temporary envs on the stack
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

### Escaped = in command name
# foo=bar is in the 'spec/bin' dir.
foo\=bar
## stdout: HI

### Env binding not allowed before compound command
# bash gives exit code 2 for syntax error, because of 'do'.
# dash gives 0 because there is stuff after for?  Should really give an error.
# mksh gives acceptable error of 1.
FOO=bar for i in a b; do printenv.py $FOO; done
## BUG dash status: 0
## OK  mksh status: 1
## status: 2

### Trying to run keyword 'for'
FOO=bar for
## status: 127

### Empty env binding
EMPTY= printenv.py EMPTY
## stdout:

### Assignment doesn't do word splitting
words='one two'
a=$words
argv.py "$a"
## stdout: ['one two']

### Assignment doesn't do glob expansion
touch _tmp/z.Z _tmp/zz.Z
a=_tmp/*.Z
argv.py "$a"
# stdout: ['_tmp/*.Z']

### Env binding in readonly/declare disallowed
# I'm disallowing this in the oil shell, because it doesn't work in bash!
# (v=None vs v=foo)
# assert status 2 for parse error, but allow stdout v=None/status 0 for
# existing implementations.
FOO=foo readonly v=$(printenv.py FOO)
echo "v=$v"
# OK bash/dash/mksh stdout: v=None
# OK bash/dash/mksh status: 0
# status: 2

### local -a
# nixpkgs setup.sh uses this (issue #26)
f() {
  local -a array=(x y z)
  argv.py "${array[@]}"
}
f
# stdout: ['x', 'y', 'z']
# N-I dash stdout-json: ""
# N-I dash status: 2
# N-I mksh stdout-json: ""
# N-I mksh status: 1

### declare -a
# nixpkgs setup.sh uses this (issue #26)
declare -a array=(x y z)
argv.py "${array[@]}"
# stdout: ['x', 'y', 'z']
# N-I dash stdout-json: ""
# N-I dash status: 2
# N-I mksh stdout-json: ""
# N-I mksh status: 1

### typeset -a a[1]=a a[3]=c
# declare works the same way in bash, but not mksh.
# spaces are NOT allowed here.
typeset -a a[1*1]=x a[1+2]=z
argv.py "${a[@]}"
# stdout: ['x', 'z']
# N-I dash stdout-json: ""
# N-I dash status: 2

### indexed LHS without spaces is allowed
a[1 * 1]=x a[ 1 + 2 ]=z
argv.py "${a[@]}"
# stdout: ['x', 'z']
# N-I dash stdout-json: ""
# N-I dash status: 2

### declare -f 
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

### declare -p 
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

### typeset -f 
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

### typeset -p 
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
