## oils_failures_allowed: 8
## compare_shells: bash

# TODO:
# zsh dash ash

#### type -t -> function
f() { echo hi; }
type -t f
## stdout: function

#### type -t -> alias
shopt -s expand_aliases
alias foo=bar
type -t foo
## stdout: alias

#### type -t -> builtin
type -t echo read : [ declare local
## STDOUT:
builtin
builtin
builtin
builtin
builtin
builtin
## END

#### type -t -> keyword
type -t for time ! fi do {
## STDOUT: 
keyword
keyword
keyword
keyword
keyword
keyword
## END

#### type -t control flow

# this differs from bash, but don't lie!
type -t break continue return exit
## STDOUT:
keyword
keyword
keyword
keyword
## END
## OK bash STDOUT:
builtin
builtin
builtin
builtin
## END


#### type -t -> file
type -t find xargs
## STDOUT: 
file
file
## END

#### type -t doesn't find non-executable (like command -v)
PATH="$TMP:$PATH"
touch $TMP/non-executable
type -t non-executable
## STDOUT:
## END
## status: 1
## BUG bash STDOUT:
file
## END
## BUG bash status: 0

#### type -t -> not found
type -t echo ZZZ find =
echo status=$?
## STDOUT: 
builtin
file
status=1
## END
## STDERR:
## END

#### type -> not found
type zz 2>err.txt
echo status=$?
grep -o 'not found' err.txt
## STDOUT:
status=1
not found
## END

#### type -p and -P builtin -> file
touch /tmp/{mv,tar,grep}
chmod +x /tmp/{mv,tar,grep}
PATH=/tmp:$PATH

type -p mv tar grep
echo --
type -P mv tar grep
## STDOUT:
/tmp/mv
/tmp/tar
/tmp/grep
--
/tmp/mv
/tmp/tar
/tmp/grep
## END

#### type -p builtin -> not found
type -p FOO BAR NOT_FOUND
## status: 1
## STDOUT:
## END

#### type -p builtin -> not a file
type -p cd type builtin command
## STDOUT:
## END

#### type -P builtin -> not found
type -P FOO BAR NOT_FOUND
## status: 1
## STDOUT:
## END

#### type -P builtin -> not a file
type -P cd type builtin command
## status: 1
## STDOUT:
## END

#### type -P builtin -> not a file but file found
touch /tmp/{mv,tar,grep}
chmod +x /tmp/{mv,tar,grep}
PATH=/tmp:$PATH

mv () { ls; }
tar () { ls; }
grep () { ls; }
type -P mv tar grep cd builtin command type
## status: 1
## STDOUT:
/tmp/mv
/tmp/tar
/tmp/grep
## END

#### type -f builtin -> not found
type -f FOO BAR NOT FOUND
## status: 1

#### type -f builtin -> function and file exists
touch /tmp/{mv,tar,grep}
chmod +x /tmp/{mv,tar,grep}
PATH=/tmp:$PATH

mv () { ls; }
tar () { ls; }
grep () { ls; }
type -f mv tar grep
## STDOUT:
/tmp/mv is a file
/tmp/tar is a file
/tmp/grep is a file
## OK bash STDOUT:
mv is /tmp/mv
tar is /tmp/tar
grep is /tmp/grep
## END

#### type -a -> function; prints shell source code
f () { :; }
type -a f
## STDOUT:
f is a function
f () 
{ 
    :
}
## END

#### type -ap -> function
f () { :; }
type -ap f
## STDOUT:
## END

#### type -a -> alias; prints alias definition
shopt -s expand_aliases
alias ll="ls -lha"
type -a ll
## stdout: ll is aliased to `ls -lha'

#### type -ap -> alias
shopt -s expand_aliases
alias ll="ls -lha"
type -ap ll
## STDOUT:
## END

#### type -a -> builtin
type -a cd
## stdout: cd is a shell builtin

#### type -ap -> builtin
type -ap cd
## STDOUT:
## END

#### type -a -> keyword
type -a while
## stdout: while is a shell keyword

#### type -a -> file
touch _tmp/date
chmod +x _tmp/date
PATH=/bin:_tmp  # control output

type -a date

## STDOUT:
date is /bin/date
date is _tmp/date
## END

#### type -ap -> file
touch _tmp/date
chmod +x _tmp/date
PATH=/bin:_tmp  # control output

type -ap date
## STDOUT:
/bin/date
_tmp/date
## END

#### type -a -> builtin and file
touch _tmp/pwd
chmod +x _tmp/pwd
PATH=/bin:_tmp  # control output

type -a pwd
## STDOUT:
pwd is a shell builtin
pwd is /bin/pwd
pwd is _tmp/pwd
## END

#### type -ap -> builtin and file
touch _tmp/pwd
chmod +x _tmp/pwd
PATH=/bin:_tmp  # control output

type -ap pwd
## STDOUT:
/bin/pwd
_tmp/pwd
## END

#### type -a -> executable not in PATH
touch /tmp/executable
chmod +x /tmp/executable
type -a executable
## status: 1

