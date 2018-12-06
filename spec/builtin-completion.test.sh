#!/usr/bin/env bash

#### -A function prints functions
add () { expr 4 + 4; }
div () { expr 6 / 2; }
ek () { echo hello; }
__ec () { echo hi; }
_ab () { expr 10 % 3; }
compgen -A function
echo --
compgen -A function _
## status: 0
## STDOUT:
__ec
_ab
add
div
ek
--
__ec
_ab
## END

#### Invalid syntax
compgen -A foo
echo status=$?
## stdout: status=2

#### how compgen calls completion functions
foo_complete() {
  argv.py argv "$@"
  argv.py COMP_WORDS "${COMP_WORDS[@]}"
  argv.py COMP_CWORD "${COMP_CWORD}"
  argv.py COMP_LINE "${COMP_LINE}"
  argv.py COMP_POINT "${COMP_POINT}"
  #return 124
  COMPREPLY=(one two three)
}
compgen -F foo_complete foo a b c
## STDOUT:
['argv', 'compgen', 'foo', '']
['COMP_WORDS']
['COMP_CWORD', '-1']
['COMP_LINE', '']
['COMP_POINT', '0']
one
two
three
## END

#### complete -o -F (git)
foo() { echo foo; }
wrapper=foo
complete -o default -o nospace -F $wrapper git
## status: 0

#### compopt -o (git)
# NOTE: Have to be executing a completion function
compopt -o filenames +o nospace
## status: 1

#### compgen -f on invalid  dir
compgen -f /non-existing-dir/
## status: 1
## stdout-json: ""

#### compgen -f
mkdir -p $TMP/compgen
touch $TMP/compgen/{one,two,three}
cd $TMP/compgen
compgen -f | sort
echo --
compgen -f t | sort
## STDOUT:
one
three
two
--
three
two
## END

#### compgen -v with local vars
v1_global=0
f() {
  local v2_local=0	 
  compgen -v v
}
f
## STDOUT:
v1_global
v2_local
## END

#### compgen -v on unknown var
compgen -v __nonexistent__
## status: 1
## stdout-json: ""

#### compgen -v P
cd > /dev/null  # for some reason in bash, this makes PIPESTATUS appear!
compgen -v P | grep -E '^PATH|PWD' | sort
## STDOUT:
PATH
PWD
## END

#### compgen with actions: function / variable / file 
mkdir -p $TMP/compgen2
touch $TMP/compgen2/PA_FILE_{1,2}
cd $TMP/compgen2  # depends on previous test above!
PA_FUNC() { echo P; }
Q_FUNC() { echo Q; }
compgen -A function -A variable -A file PA
## STDOUT:
PA_FUNC
PATH
PA_FILE_1
PA_FILE_2
## END

#### compgen with actions: alias, setopt
alias v_alias='ls'
alias v_alias2='ls'
alias a1='ls'
compgen -A alias -A setopt v
## STDOUT:
v_alias
v_alias2
verbose
vi
## END

#### compgen with actions: shopt
compgen -A shopt -P [ -S ] nu
## STDOUT:
[nullglob]
## END

#### compgen with action and suffix: helptopic
compgen -A helptopic -S ___ fa
## STDOUT:
false___
## END

#### compgen -A directory
compgen -A directory b
## STDOUT:
bin
benchmarks
build
## END

#### compgen -W 'one two three'
compgen -W 'one two three'
echo --
compgen -W 'w1 w2 three' -A directory w
echo --
compgen -A directory -W 'w1 w2 three' w  # order doesn't matter
## STDOUT:
one
two
three
--
web
w1
w2
--
web
w1
w2
## END

#### compgen -A command completes external commands
# NOTE: this test isn't hermetic
compgen -A command xarg
echo status=$?
## STDOUT:
xargs
status=0
## END

#### compgen -A command completes functions and aliases
myfunc() { echo ; }
myfunc2() { echo ; }
alias myalias=foo
compgen -A command my
echo status=$?
## STDOUT:
myalias
myfunc
myfunc2
status=0
## END

#### compgen -A command completes builtins and keywords
compgen -A command eva
echo status=$?
compgen -A command whil
echo status=$?
## STDOUT:
eval
status=0
while
status=0
## END

#### complete with nonexistent function
complete -F invalidZZ -D
echo status=$?
## stdout: status=2
## BUG bash stdout: status=0

#### complete with no action
complete foo
echo status=$?
## stdout: status=2
## BUG bash stdout: status=0
