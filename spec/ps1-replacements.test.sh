#!/usr/bin/env bash
#
# For testing the Python sketch

#### sh -i
echo 'echo foo' | PS1='$ ' $SH --norc -i
## STDOUT:
foo
## END
## STDERR:
$ echo foo
$ exit
## END

#### constant string
PS1='$ '
echo "${PS1@P}"
## STDOUT:
$ 
## END

#### hostname
PS1='\h '
test "${PS1@P}" = "$(hostname) "
echo status=$?
## STDOUT:
status=0
## END
