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

#### \1004
PS1='\1004$'
echo "${PS1@P}"
## STDOUT:
@4$
## END

#### \555 is beyond max octal byte of \377 and wrapped to m
PS1='\555$'
test "${PS1@P}" = "m$"
echo status=$?
## STDOUT:
status=0
## END

#### \x55 hex literals not supported
PS1='[\x55]'
echo "${PS1@P}"
## STDOUT:
[\x55]
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
USER=$(whoami)
test "${PS1@P}" = "${USER} "
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
