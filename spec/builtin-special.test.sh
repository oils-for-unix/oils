## oils_failures_allowed: 3
## compare_shells: bash dash mksh zsh ash

# POSIX rule about special builtins pointed at:
#
# https://www.reddit.com/r/oilshell/comments/5ykpi3/oildev_is_alive/

#### Prefix assignments persist after special builtins, like : (set -o posix)
case $SH in
  bash)
    set -o posix
    ;;
esac

foo=bar :
echo foo=$foo

# Not true when you use 'builtin'
z=Z builtin :
echo z=$Z

## STDOUT:
foo=bar
z=
## END

## BUG zsh STDOUT:
foo=
z=
## END

#### readonly is special and prefix assignments persist (set -o posix)

# Bash only implements it behind the posix option
case $SH in
  bash)
    # for bash
    set -o posix
    ;;
esac
foo=bar readonly spam=eggs
echo foo=$foo
echo spam=$spam

# should NOT be exported
printenv.py foo
printenv.py spam

## STDOUT:
foo=bar
spam=eggs
None
None
## END

## OK bash/osh STDOUT:
foo=bar
spam=eggs
bar
None
## END

#### Special builtins can't be redefined as shell functions : (set -o posix)
case $SH in
  bash)
    set -o posix
    ;;
esac

eval 'echo hi'

eval() {
  echo 'sh func' "$@"
}

eval 'echo hi'

## status: 2
## STDOUT:
hi
## END

## BUG mksh status: 0
## BUG mksh STDOUT:
hi
hi
## END

## BUG zsh status: 0
## BUG zsh STDOUT:
hi
sh func echo hi
## END

#### Non-special builtins CAN be redefined as functions
test -n "$BASH_VERSION" && set -o posix
true() {
  echo 'true func'
}
true hi
echo status=$?
## STDOUT:
true func
status=0
## END

#### true is not special; prefix assignments don't persist
foo=bar true
echo $foo
## stdout:

#### Shift is special and the whole script exits if it returns non-zero
$SH -c '
if test -n "$BASH_VERSION"; then
  set -o posix
fi
set -- a b
shift 3
echo status=$?
'
if test "$?" != 0; then
  echo 'non-zero status'
fi

## STDOUT:
non-zero status
## END

## BUG bash/zsh/ash status: 0
## BUG bash/zsh/ash STDOUT:
status=1
## END

#### set is special and fails, even if using || true
$SH -c '
shopt -s invalid_ || true
echo ok
set -o invalid_ || true
echo should not get here
'
if test "$?" != 0; then
  echo 'non-zero status'
fi

## STDOUT:
ok
non-zero status
## END

## BUG bash/ash status: 0
## BUG bash/ash STDOUT:
ok
should not get here
## END

#### bash 'type' gets confused - says 'function', but runs builtin
case $SH in dash|mksh|zsh|ash) exit ;; esac

echo TRUE
type -t true  # builtin
true() { echo true func; }
type -t true  # now a function
echo ---

echo EVAL

type -t eval  # builtin
# define function before set -o posix
eval() { echo "$1"; }
# bash runs the FUNCTION, but OSH finds the special builtin
# OSH doesn't need set -o posix
eval 'echo before posix'

if test -n "$BASH_VERSION"; then
  # this makes the eval definition invisible!
  set -o posix
fi

eval 'echo after posix'  # this is the builtin eval
# it claims it's a function, but it's a builtin
type -t eval

# it finds the function and the special builtin
#type -a eval

## OK bash STDOUT:
TRUE
builtin
function
---
EVAL
builtin
echo before posix
after posix
function
## END

## OK osh STDOUT:
TRUE
builtin
function
---
EVAL
builtin
before posix
after posix
function
## END

## N-I dash/mksh/zsh/ash STDOUT:
## END

#### command, builtin - both can be redefined, not special (regression)
case $SH in dash|ash) exit ;; esac

builtin echo b
command echo c

builtin() {
  echo builtin-redef "$@"
}

command() {
  echo command-redef "$@"
}

builtin echo b
command echo c

## STDOUT:
b
c
builtin-redef echo b
command-redef echo c
## END
## N-I dash/ash STDOUT:
## END
