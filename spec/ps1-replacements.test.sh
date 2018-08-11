#!/usr/bin/env bash
#
# For testing the Python sketch

#### constant string
#'echo 1' | PS1='$ ' $SH --norc -i
PS1='$ '
echo "${PS1@P}"
## STDOUT:
$ 
## END

#### hostname
#'echo 1' | PS1='$ ' $SH --norc -i
PS1='\h '
test "${PS1@P}" = "$(hostname) "
echo status=$?
## STDOUT:
status=0
## END
