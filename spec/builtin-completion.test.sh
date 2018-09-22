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
compgen -v P | grep -E 'PATH|PWD' | sort
## STDOUT:
PATH
PWD
## END

#### Three compgens combined
mkdir -p $TMP/compgen2
touch $TMP/compgen2/PA_FILE_{1,2}
cd $TMP/compgen2  # depends on previous test above!
PA_FUNC() { echo P; }
Q_FUNC() { echo Q; }
compgen -A function -A file -A variable PA
## STDOUT:
PA_FUNC
PATH
PA_FILE_1
PA_FILE_2
## END

#### complete with nonexistent function
complete -F invalidZZ -D
echo status=$?
## stdout: status=1
## BUG bash stdout: status=0

#### complete with no action
complete foo
echo status=$?
## stdout: status=1
## BUG bash stdout: status=0
