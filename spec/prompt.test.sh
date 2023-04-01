
#### sh -i
# Notes:
# - OSH prompt goes to stdout and bash goes to stderr
# - This test seems to fail on the system bash, but succeeds with spec-bin/bash
echo 'echo foo' | PS1='[prompt] ' $SH --rcfile /dev/null -i >out.txt 2>err.txt
fgrep -q '[prompt]' out.txt err.txt
echo match=$?
## STDOUT:
match=0
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

#### \A for 24 hour time
PS1='foo \A bar'
echo "${PS1@P}" | egrep -q 'foo [0-9][0-9]:[0-9][0-9] bar'
echo matched=$?
## STDOUT:
matched=0
## END

#### \D{%H:%M} for strftime
PS1='foo \D{%H:%M} bar'
echo "${PS1@P}" | egrep -q 'foo [0-9][0-9]:[0-9][0-9] bar'
echo matched=$?

PS1='foo \D{%H:%M:%S} bar'
echo "${PS1@P}" | egrep -q 'foo [0-9][0-9]:[0-9][0-9]:[0-9][0-9] bar'
echo matched=$?

## STDOUT:
matched=0
matched=0
## END

#### \D{} for locale specific strftime

# In bash y.tab.c uses %X when string is empty
# This doesn't seem to match exactly, but meh for now.

PS1='foo \D{} bar'
echo "${PS1@P}" | egrep -q '^foo [0-9][0-9]:[0-9][0-9]:[0-9][0-9]( ..)? bar$'
echo matched=$?
## STDOUT:
matched=0
## END

#### \s and \v for shell and version
PS1='foo \s bar'
echo "${PS1@P}" | egrep -q '^foo (bash|osh) bar$'
echo match=$?

PS1='foo \v bar'
echo "${PS1@P}" | egrep -q '^foo [0-9.]+ bar$'
echo match=$?

## STDOUT:
match=0
match=0
## END

#### @P with array
$SH -c 'echo ${@@P}' dummy a b c
echo status=$?
$SH -c 'echo ${*@P}' dummy a b c
echo status=$?
$SH -c 'a=(x y); echo ${a@P}' dummy a b c
echo status=$?
## STDOUT:
a b c
status=0
a b c
status=0
x
status=0
## END
## OK osh STDOUT:
status=1
status=1
x
status=0
## END

#### default PS1
#flags='--norc --noprofile'
flags='--rcfile /dev/null'

$SH $flags -i -c 'echo "_${PS1}_"'

## STDOUT:
_\s-\v\$ _
## END

