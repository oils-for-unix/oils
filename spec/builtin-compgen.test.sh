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
