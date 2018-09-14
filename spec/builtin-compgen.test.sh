#!/usr/bin/env bash

#### -A function prints functions
add () { expr 4 + 4; }
div () { expr 6 / 2; }
ek () { echo hello; }
__ec () { echo hi; }
_ab () { expr 10 % 3; }
compgen -A function
## status: 0
## STDOUT:
__ec
_ab
add
div
ek
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

#### compgen -v on unknown var
compgen -v __nonexistent__
## status: 1
## stdout-json: ""

#### compgen -v P
cd > /dev/null  # for some reason in bash, this makes PIPESTATUS appear!
compgen -v P
## STDOUT:
PATH
PIPESTATUS
PPID
PS4
PWD
## END

#### Three compgens combined
mkdir -p $TMP/compgen2
touch $TMP/compgen2/{P1,P2}_FILE
cd $TMP/compgen2  # depends on previous test above!
P_FUNC() { echo P; }
Q_FUNC() { echo Q; }
compgen -A function -A file -A variable P
## STDOUT:
P_FUNC
PATH
PIPESTATUS
PPID
PS4
PWD
P1_FILE
P2_FILE
## END
