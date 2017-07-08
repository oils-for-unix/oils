#!/usr/bin/env bash
#
# POSIX rule about special builtins pointed at:
#
# https://www.reddit.com/r/oilshell/comments/5ykpi3/oildev_is_alive/

### : is special and prefix assignments persist after special builtins
# Bash only implements it behind the posix option
test -n "$BASH_VERSION" && set -o posix
foo=bar :
echo $foo
# stdout: bar

### true is not special
foo=bar true
echo $foo
# stdout:

### Shift is special and the whole script exits if it returns non-zero
test -n "$BASH_VERSION" && set -o posix
set -- a b
shift 3
echo status=$?
# stdout-json: ""
# status: 1
# OK dash status: 2
# BUG bash status: 0
# BUG bash stdout-json: "status=1\n"

### Special builtins can't be redefined as functions
# bash manual says they are 'found before' functions.
test -n "$BASH_VERSION" && set -o posix
export() {
  echo 'export func'
}
export hi
echo status=$?
# status: 2
# BUG mksh status: 0
# BUG mksh stdout: status=0

### Non-special builtins CAN be redefined as functions
test -n "$BASH_VERSION" && set -o posix
true() {
  echo 'true func'
}
true hi
echo status=$?
# stdout-json: "true func\nstatus=0\n"
