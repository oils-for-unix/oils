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

#### compgen -f
compgen -f /non-existing-dir/
## status: 1

#### compgen -v
compgen -v __gitcomp_builtin
## status: 1
