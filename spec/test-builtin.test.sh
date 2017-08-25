#!/usr/bin/env bash
#
# NOTES:
# - osh is using the external binary.
# - because ! -a -o ( ) are the same, we can share logic with [[.

### test with extra args is syntax error
test -n x ]
echo status=$?
test -n x y
echo status=$?
# stdout-json: "status=2\nstatus=2\n"

### ] syntax errors
[ -n x  # missing ]
echo status=$?
[ -n x ] y  # extra arg after ]
echo status=$?
[ -n x y  # extra arg
echo status=$?
# stdout-json: "status=2\nstatus=2\nstatus=2\n"

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

### test whether == is empty
[ == ] && echo true
[ -n == ] && echo true
# stdout-json: "true\ntrue\n"

### ( )
[ -z '' -a '(' ! -z x ')' ] && echo true
# stdout: true

### ( ) ! -a -o with system version of [
command [ --version
command [ -z '' -a '(' ! -z x ')' ] && echo true
# stdout: true

### == is alias for =
[ a = a ] && echo true
[ a == a ] && echo true
# stdout-json: "true\ntrue\n"
# BUG dash stdout-json: "true\n"
# BUG dash status: 2

### [ with op variable
# OK -- parsed AFTER evaluation of vars
op='='
[ a $op a ] && echo true
[ a $op b ] || echo false
# status: 0
# stdout-json: "true\nfalse\n"

### [ with unquoted empty var
empty=''
[ $empty = '' ] && echo true
# status: 2

### [ compare with literal -f
# Hm this is the same
var=-f
[ $var = -f ] && echo true
[ '-f' = $var ] && echo true
# stdout-json: "true\ntrue\n"

### [ '(' ] is treated as literal
[ '(' ]
echo status=$?
# stdout: status=0

### [ '(' foo ] is runtime syntax error
[ '(' foo ]
echo status=$?
# stdout: status=2

### empty ! is treated as literal
[ '!' ]
echo status=$?
# stdout: status=0

### -z '>' implies two token lookahead
[ -z ] && echo true  # -z is operand
[ -z '>' ] || echo false  # -z is operator
[ -z '>' -- ] && echo true  # -z is operand
# stdout-json: "true\nfalse\ntrue\n"

