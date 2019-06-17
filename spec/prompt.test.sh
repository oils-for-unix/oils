#!/usr/bin/env bash

#### sh -i
# This fails because OSH prompt goes to stdout, and other differences. It's
# probably OK to be honest.
echo 'echo foo' | PS1='$ ' $SH --rcfile /dev/null -i
## STDOUT:
foo
## END
## STDERR:
$ echo foo
$ exit
## END

#### \[\] are non-printing
PS1='\[foo\]\$'
echo "${PS1@P}"
## STDOUT:
foo$
## END

#### literal escapes
PS1='\a\e\r\n'
echo "${PS1@P}"
## stdout-json: "\u0007\u001b\r\n\n"

#### special case for $
# NOTE: This might be broken for # but it's hard to tell since we don't have
# root.  Could inject __TEST_EUID or something.
PS1='$'
echo "${PS1@P}"
PS1='\$'
echo "${PS1@P}"
PS1='\\$'
echo "${PS1@P}"
PS1='\\\$'
echo "${PS1@P}"
PS1='\\\\$'
echo "${PS1@P}"
## STDOUT:
$
$
$
\$
\$
## END

#### PS1 evaluation order
x='\'
y='h'
PS1='$x$y'
echo "${PS1@P}"
## STDOUT:
\h
## END

#### PS1 evaluation order 2
foo=foo_value
dir=$TMP/'$foo'  # Directory name with a dollar!
mkdir -p $dir
cd $dir
PS1='\w $foo'
test "${PS1@P}" = "$PWD foo_value"
echo status=$?
## STDOUT:
status=0
## END

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

# NOTE: This test is not hermetic.  On my machine the short and long host name
# are the same.

PS1='\h '
test "${PS1@P}" = "$(hostname -s) "  # short name
echo status=$?
PS1='\H '
test "${PS1@P}" = "$(hostname) "
echo status=$?
## STDOUT:
status=0
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

#### \W is basename of working dir
PS1='\W '
test "${PS1@P}" = "$(basename $PWD) "
echo status=$?
## STDOUT:
status=0
## END
