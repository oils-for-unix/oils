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

#### [] are non-printing
PS1='\[foo\]\$'
echo "${PS1@P}"
## STDOUT:
foo$
## END

#### literal escapes
PS1='\a\e\r\n'
echo "${PS1@P}"
## stdout-json: "\u0007\u001b\r\n\n"

#### \1004
PS1='\1004$'
echo "${PS1@P}"
## STDOUT:
@4$
## END

#### \001 octal literals are supported
PS1='[\045]'
echo "${PS1@P}"
## STDOUT:
[%]
## END

#### \555 is beyond max octal byte of \377 and wrapped to m
PS1='\555$'
echo "${PS1@P}"
## STDOUT:
m$
## END

#### \x55 hex literals not supported
PS1='[\x55]'
echo "${PS1@P}"
## STDOUT:
[\x55]
## END

#### Single backslash
PS1='\'
echo "${PS1@P}"
## BUG bash stdout-json: "\\\u0002\n"
## STDOUT:
\
## END

#### Escaped backslash
PS1='\\'
echo "${PS1@P}"
## BUG bash stdout-json: "\\\u0002\n"
## STDOUT:
\
## END

#### \0001 octal literals are not supported
PS1='[\0455]'
echo "${PS1@P}"
## STDOUT:
[%5]
## END

#### \u0001 unicode literals not supported
PS1='[\u0001]'
USER=$(whoami)
test "${PS1@P}" = "[${USER}0001]"
echo status=$?
## STDOUT:
status=0
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
PS1='\u '
USER=$(whoami)
test "${PS1@P}" = "${USER} "
echo status=$?
## STDOUT:
status=0
## END

#### current working dir
PS1='\w '
test "${PS1@P}" = "${PWD} "
echo status=$?
## STDOUT:
status=0
## END
