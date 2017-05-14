#!/bin/bash
#
# POSIX rule about special builtins pointed at:
#
# https://www.reddit.com/r/oilshell/comments/5ykpi3/oildev_is_alive/

### Rule about special builtins -- : is special
test -n "$BASH_VERSION" && set -o posix  # Bash only implements it behind the posix option
foo=bar :
echo $foo
# stdout: bar

### Rule about special builtins -- true is not special
foo=bar true
echo $foo
# stdout:
