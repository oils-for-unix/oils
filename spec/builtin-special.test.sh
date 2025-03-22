## oils_failures_allowed: 3
## compare_shells: bash dash mksh zsh ash


# POSIX rule about special builtins pointed at:
#
# https://www.reddit.com/r/oilshell/comments/5ykpi3/oildev_is_alive/

#### : is special and prefix assignments persist after special builtins
case $SH in
  dash|zsh|*osh)
    ;;
  *)
    # for bash
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

#### readonly is special and prefix assignments persist

# Bash only implements it behind the posix option
case $SH in
  dash|zsh|*osh)
    ;;
  *)
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
## BUG bash STDOUT:
foo=bar
spam=eggs
bar
None
## END

#### true is not special
foo=bar true
echo $foo
## stdout:

#### Shift is special and the whole script exits if it returns non-zero
if test -n "$BASH_VERSION"; then
  set -o posix
fi
set -- a b
shift 3
echo status=$?

## status: 1
## STDOUT:
## END

## OK dash status: 2

## BUG bash/zsh/ash status: 0
## BUG bash/zsh/ash STDOUT:
status=1
## END

#### set is special and fails, even if using || true
shopt -s invalid_ || true
echo ok
set -o invalid_ || true
echo should not get here

## status: 1
## STDOUT:
ok
## END

## OK dash status: 2

## BUG bash/ash status: 0
## BUG bash/ash STDOUT:
ok
should not get here
## END

#### Special builtins can't be redefined as functions (set -o posix)

# bash manual says they are 'found before' functions.
if test -n "$BASH_VERSION"; then
  set -o posix
fi

export() {
  echo 'export func'
}
export hi
echo status=$?
## status: 2
## BUG mksh/zsh status: 0
## BUG mksh/zsh STDOUT:
status=0
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
