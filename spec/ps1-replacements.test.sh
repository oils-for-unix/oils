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

#### username
#'echo 1' | PS1='$ ' $SH --norc -i
PS1='\u '
test "${PS1@P}" = "$(whoami) "
echo status=$?
## STDOUT:
status=0
## END

#### uid (not root)
#'echo 1' | PS1='$ ' $SH --norc -i
PS1='\$ '
test "${PS1@P}" = "$ "
echo status=$?
## STDOUT:
status=0
## END

#### current working dir
#'echo 1' | PS1='$ ' $SH --norc -i
PS1='\w '
test "${PS1@P}" = "${PWD} "
echo status=$?
## STDOUT:
status=0
## END
