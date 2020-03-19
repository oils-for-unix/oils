#!/usr/bin/env bash
#
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
## STDOUT:
foo=bar
## END
## BUG zsh STDOUT:
foo=
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
test -n "$BASH_VERSION" && set -o posix
set -- a b
shift 3
echo status=$?
## stdout-json: ""
## status: 1
## OK dash status: 2
## BUG bash/zsh status: 0
## BUG bash/zsh STDOUT:
status=1
## END

#### set is special and fails, even if using || true
shopt -s invalid_ || true
echo ok
set -o invalid_ || true
echo should not get here
## STDOUT:
ok
## END
## status: 1
## OK dash status: 2
## BUG bash status: 0
## BUG bash STDOUT:
ok
should not get here
## END

#### Special builtins can't be redefined as functions
# bash manual says they are 'found before' functions.
test -n "$BASH_VERSION" && set -o posix
export() {
  echo 'export func'
}
export hi
echo status=$?
## status: 2
## BUG mksh/zsh status: 0
## BUG mksh/zsh stdout: status=0

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
