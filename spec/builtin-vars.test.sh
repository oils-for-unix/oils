#!/usr/bin/env bash
#
# Tests for builtins having to do with variables: export, readonly, unset, etc.
#
# Also see assign.test.sh.

#### Export sets a global variable
# Even after you do export -n, it still exists.
f() { export GLOBAL=X; }
f
echo $GLOBAL
printenv.py GLOBAL
## stdout-json: "X\nX\n"

#### Export sets a global variable that persists after export -n
f() { export GLOBAL=X; }
f
echo $GLOBAL
printenv.py GLOBAL
export -n GLOBAL
echo $GLOBAL
printenv.py GLOBAL
## STDOUT: 
X
X
X
None
## END
## N-I mksh/dash STDOUT:
X
X
## END
## N-I mksh status: 1
## N-I dash status: 2
## N-I zsh STDOUT:
X
X
X
X
## END

#### export -n undefined is ignored
set -o errexit
export -n undef
echo status=$?
## stdout: status=0
## N-I mksh/dash/zsh stdout-json: ""
## N-I mksh status: 1
## N-I dash status: 2
## N-I zsh status: 1

#### Export a global variable and unset it
f() { export GLOBAL=X; }
f
echo $GLOBAL
printenv.py GLOBAL
unset GLOBAL
echo $GLOBAL
printenv.py GLOBAL
## stdout-json: "X\nX\n\nNone\n"

#### Export existing global variables
G1=g1
G2=g2
export G1 G2
printenv.py G1 G2
## stdout-json: "g1\ng2\n"

#### Export existing local variable
f() {
  local L1=local1
  export L1
  printenv.py L1
}
f
printenv.py L1
## stdout-json: "local1\nNone\n"

#### Export a local that shadows a global
V=global
f() {
  local V=local1
  export V
  printenv.py V
}
f
printenv.py V  # exported local out of scope; global isn't exported yet
export V
printenv.py V  # now it's exported
## stdout-json: "local1\nNone\nglobal\n"

#### Export a variable before defining it
export U
U=u
printenv.py U
## stdout: u

#### Exporting a parent func variable (dynamic scope)
# The algorithm is to walk up the stack and export that one.
inner() {
  export outer_var
  echo "inner: $outer_var"
  printenv.py outer_var
}
outer() {
  local outer_var=X
  echo "before inner"
  printenv.py outer_var
  inner
  echo "after inner"
  printenv.py outer_var
}
outer
## stdout-json: "before inner\nNone\ninner: X\nX\nafter inner\nX\n"

#### Dependent export setting
# FOO is not respected here either.
export FOO=foo v=$(printenv.py FOO)
echo "v=$v"
## stdout: v=None

#### Exporting a variable doesn't change it
old=$PATH
export PATH
new=$PATH
test "$old" = "$new" && echo "not changed"
## stdout: not changed

#### assign to readonly variable
# bash doesn't abort unless errexit!
readonly foo=bar
foo=eggs
echo "status=$?"  # nothing happens
## status: 1
## BUG bash stdout: status=1
## BUG bash status: 0
## OK dash/mksh status: 2

#### assign to readonly variable - errexit
set -o errexit
readonly foo=bar
foo=eggs
echo "status=$?"  # nothing happens
## status: 1
## OK dash/mksh status: 2

#### Unset a variable
foo=bar
echo foo=$foo
unset foo
echo foo=$foo
## stdout-json: "foo=bar\nfoo=\n"

#### Unset exit status
V=123
unset V
echo status=$?
## stdout: status=0

#### Unset nonexistent variable
unset ZZZ
echo status=$?
## stdout: status=0

#### Unset readonly variable
# dash and zsh abort the whole program.   OSH doesn't?
readonly R=foo
unset R
echo status=$?
## status: 0
## stdout: status=1
## OK dash status: 2
## OK dash stdout-json: ""
## OK zsh status: 1
## OK zsh stdout-json: ""

#### Unset a function without -f
f() {
  echo foo
}
f
unset f
f
## stdout: foo
## status: 127
## N-I dash/mksh/zsh status: 0
## N-I dash/mksh/zsh STDOUT:
foo
foo
## END

#### Unset has dynamic scope
f() {
  unset foo
}
foo=bar
echo foo=$foo
f
echo foo=$foo
## stdout-json: "foo=bar\nfoo=\n"

#### Unset invalid variable name
unset %
echo status=$?
## STDOUT:
status=2
## END
## OK bash/mksh STDOUT:
status=1
## END
## BUG zsh STDOUT:
status=0
## END
# dash does a hard failure!
## OK dash stdout-json: ""
## OK dash status: 2

#### Unset nonexistent variable
unset _nonexistent__
echo status=$?
## STDOUT:
status=0
## END

#### Unset -v
foo() {
  echo "function foo"
}
foo=bar
unset -v foo
echo foo=$foo
foo
## stdout-json: "foo=\nfunction foo\n"

#### Unset -f
foo() {
  echo "function foo"
}
foo=bar
unset -f foo
echo foo=$foo
foo
echo status=$?
## stdout-json: "foo=bar\nstatus=127\n"

#### Unset array member
a=(x y z)
unset 'a[1]'
echo "${a[@]}" len="${#a[@]}"
## stdout: x z len=2
## N-I dash status: 2
## N-I dash stdout-json: ""
## OK zsh stdout-json: " y z len=3\n"

#### Unset array member with expression
i=1
a=(w x y z)
unset 'a[ i - 1 ]' a[i+1]  # note: can't have space between a and [
echo "${a[@]}" len="${#a[@]}"
## stdout: x z len=2
## N-I dash status: 2
## N-I dash stdout-json: ""
## N-I zsh status: 1
## N-I zsh stdout-json: ""

#### Use local twice
f() {
  local foo=bar
  local foo
  echo $foo
}
f
## stdout: bar
## BUG zsh STDOUT:
foo=bar
bar
## END

#### Local without variable is still unset!
set -o nounset
f() {
  local foo
  echo "[$foo]"
}
f
## stdout-json: ""
## status: 1
## OK dash status: 2
# zsh doesn't support nounset?
## BUG zsh stdout: []
## BUG zsh status: 0

#### local after readonly
f() { 
  readonly y
  local x=1 y=$(( x ))
  echo y=$y
}
f
## stdout-json: ""
## status: 1
## OK dash status: 2
## BUG bash stdout: y=
## BUG bash status: 0
## BUG mksh stdout: y=0
## BUG mksh status: 0

