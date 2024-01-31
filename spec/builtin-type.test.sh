## oils_failures_allowed: 0
## compare_shells: bash zsh mksh dash ash

#### type -> keyword builtin 

type while cd

## STDOUT:
while is a shell keyword
cd is a shell builtin
## END
## OK zsh/mksh STDOUT:
while is a reserved word
cd is a shell builtin
## END

#### type -> alias function external

shopt -s expand_aliases || true  # bash

alias ll='ls -l'

f() { echo hi; }

touch _tmp/date
chmod +x _tmp/date
PATH=_tmp:/bin

# ignore quotes and backticks
# bash prints a left backtick
quotes='"`'\'

type ll f date | sed "s/[$quotes]//g"

# Note: both procs and funcs go in var namespace?  So they don't respond to
# 'type'?

## STDOUT:
ll is an alias for ls -l
f is a shell function
date is _tmp/date
## END
## OK ash STDOUT:
ll is an alias for ls -l
f is a function
date is _tmp/date
## END
## OK mksh STDOUT:
ll is an alias for ls -l
f is a function
date is a tracked alias for _tmp/date
## END
## OK bash STDOUT:
ll is aliased to ls -l
f is a function
f () 
{ 
    echo hi
}
date is _tmp/date
## END

#### type of relative path

touch _tmp/file _tmp/ex
chmod +x _tmp/ex

type _tmp/file _tmp/ex

# dash and ash don't care if it's executable
# mksh

## status: 1
## STDOUT:
_tmp/ex is _tmp/ex
## END

## OK mksh/zsh STDOUT:
_tmp/file not found
_tmp/ex is _tmp/ex
## END

## BUG dash/ash status: 0
## BUG dash/ash STDOUT:
_tmp/file is _tmp/file
_tmp/ex is _tmp/ex
## END

#### type -> not found

type zz 2>err.txt
echo status=$?

# for bash and OSH: print to stderr
fgrep -o 'zz: not found' err.txt || true

# zsh and mksh behave the same - status 1
# dash and ash behave the same - status 127

## STDOUT:
status=1
zz: not found
## END

## OK mksh/zsh STDOUT:
zz not found
status=1
## END
## STDERR:
## END

## BUG dash/ash STDOUT:
zz: not found
status=127
## END
## BUG dash/ash STDERR:
## END
