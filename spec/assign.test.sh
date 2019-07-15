#!/usr/bin/env bash

#### Env value doesn't persist
FOO=foo printenv.py FOO
echo -$FOO-
## STDOUT:
foo
--
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
## OK  mksh/zsh status: 1
## status: 2

#### Trying to run keyword 'for'
FOO=bar for
## status: 127
## OK zsh status: 1

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
## OK bash/dash/mksh/zsh stdout: v=None
## OK bash/dash/mksh/zsh status: 0
## status: 2


#### assignments / array assignments not interpreted after 'echo'
a=1 echo b[0]=2 c=3
## stdout: b[0]=2 c=3
# zsh interprets [0] as some kind of glob
## OK zsh stdout-json: ""
## OK zsh status: 1

#### dynamic local variables
f() {
  local "$1"  # Only x is assigned here
  echo -$x-
  echo -$a-

  local $1  # x and a are assigned here
  echo -$x-
  echo -$a-
}
f 'x=y a=b'
## STDOUT:
-y a=b-
--
-y-
-b-
## END
# zsh doesn't do word splitting
## OK zsh STDOUT:
-y a=b-
--
-y a=b-
--
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
## BUG zsh status: 0

#### 'local -a x' does not set variable
set -o nounset
f() {
  local -a x
  echo $x
}
f
## status: 1
## OK dash status: 2
## BUG zsh status: 0

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
## BUG zsh stdout: o

#### 'declare -A' and then dict assignment
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


#### Modify a temporary binding
# (regression for bug found by Michael Greenberg)
f() {
  echo "x before = $x"
  x=$((x+1))
  echo "x after  = $x"
}
x=5 f
## STDOUT:
x before = 5
x after  = 6
## END

#### Reveal existence of "temp frame" (All shells disagree here!!!)
f() {
  echo "x=$x"

  x=mutated-temp  # mutate temp frame
  echo "x=$x"

  # Declare a new local
  local x='local'
  echo "x=$x"

  # Unset it
  unset x
  echo "x=$x"
}

x=global
x=temp-binding f
echo "x=$x"

## STDOUT:
x=temp-binding
x=mutated-temp
x=local
x=
x=global
## END
## BUG dash STDOUT:
x=temp-binding
x=mutated-temp
x=local
x=
x=mutated-temp
## END
## BUG bash STDOUT:
x=temp-binding
x=mutated-temp
x=local
x=global
x=global
## END
## BUG mksh STDOUT:
x=temp-binding
x=mutated-temp
x=local
x=mutated-temp
x=mutated-temp
## END
## BUG yash STDOUT:
# yash has no locals
x=temp-binding
x=mutated-temp
x=mutated-temp
x=
x=
## END

#### Test above without 'local' (which is not POSIX)
f() {
  echo "x=$x"

  x=mutated-temp  # mutate temp frame
  echo "x=$x"

  # Unset it
  unset x
  echo "x=$x"
}

x=global
x=temp-binding f
echo "x=$x"

## STDOUT:
x=temp-binding
x=mutated-temp
x=
x=global
## END
## BUG dash/mksh/yash STDOUT:
x=temp-binding
x=mutated-temp
x=
x=
## END
## BUG bash STDOUT:
x=temp-binding
x=mutated-temp
x=global
x=global
## END

#### Using ${x-default} after unsetting local shadowing a global
f() {
  echo "x=$x"
  local x='local'
  echo "x=$x"
  unset x
  echo "- operator = ${x-default}"
  echo ":- operator = ${x:-default}"
}
x=global
f
## STDOUT:
x=global
x=local
- operator = default
:- operator = default
## END
## BUG mksh STDOUT:
x=global
x=local
- operator = global
:- operator = global
## END

#### Using ${x-default} after unsetting a temp binding shadowing a global
f() {
  echo "x=$x"
  local x='local'
  echo "x=$x"
  unset x
  echo "- operator = ${x-default}"
  echo ":- operator = ${x:-default}"
}
x=global
x=temp-binding f
## STDOUT:
x=temp-binding
x=local
- operator = default
:- operator = default
## END
## BUG mksh STDOUT:
x=temp-binding
x=local
- operator = temp-binding
:- operator = temp-binding
## END
## BUG bash STDOUT:
x=temp-binding
x=local
- operator = global
:- operator = global
## END

#### static assignment doesn't split
words='a b c'
export ex=$words
glo=$words
readonly ro=$words
argv.py "$ex" "$glo" "$ro"

## STDOUT:
['a b c', 'a b c', 'a b c']
## END
## BUG dash STDOUT:
['a', 'a b c', 'a']
## END


#### aliased assignment doesn't split
shopt -s expand_aliases || true
words='a b c'
alias e=export
alias r=readonly
e ex=$words
r ro=$words
argv.py "$ex" "$ro"
## BUG dash STDOUT:
['a', 'a']
## END
## STDOUT:
['a b c', 'a b c']
## END


#### assignment using dynamic keyword splits
words='a b c'
e=export
r=readonly
$e ex=$words
$r ro=$words
argv.py "$ex" "$ro"
## STDOUT:
['a', 'a']
## END

# zsh is smart??  How does it do this?
## BUG zsh STDOUT:
['a b c', 'a b c']
## END

#### assignment using dynamic var names doesn't split
words='a b c'
arg_ex=ex=$words
arg_ro=ro=$words

# no quotes, this is split of course
export $arg_ex
readonly $arg_ro

argv.py "$ex" "$ro"

arg_ex2=ex2=$words
arg_ro2=ro2=$words

# quotes, no splitting
export "$arg_ex2"
readonly "$arg_ro2"

argv.py "$ex2" "$ro2"

## STDOUT:
['a', 'a']
['a b c', 'a b c']
## END
## BUG zsh STDOUT:
['a b c', 'a b c']
['a b c', 'a b c']
## END

#### assign and glob
cd $TMP
touch foo=a foo=b
foo=*
argv "$foo"
unset foo

export foo=*
argv "$foo"
unset foo

## STDOUT:
['*']
['*']
## END
## BUG dash STDOUT:
['*']
['b']
## END

#### declare and glob
cd $TMP
touch foo=a foo=b
typeset foo=*
argv "$foo"
unset foo
## STDOUT:
['*']
## END
## N-I dash STDOUT:
['']
## END
