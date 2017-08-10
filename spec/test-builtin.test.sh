#!/usr/bin/env bash
#
# NOTES:
# - osh is using the external binary.
# - because ! -a -o ( ) are the same, we can share logic with [[.

### empty string is false.  Equivalent to -n.
test 'a'  && echo true
test ''   || echo false
# stdout-json: "true\nfalse\n"

### -n
test -n 'a'  && echo true
test -n ''   || echo false
# stdout-json: "true\nfalse\n"

### ! -a -o
[ -z '' -a ! -z x ] && echo true
# stdout: true

### ( )
[ -z '' -a '(' ! -z x ')' ] && echo true
# stdout: true

### ( ) ! -a -o with system version of [
command [ --version
command [ -z '' -a '(' ! -z x ')' ] && echo true
# stdout: true
