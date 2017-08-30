#!/usr/bin/env bash
#
# NOTES:
# - osh is using the external binary.
# - because ! -a -o ( ) are the same, we can share logic with [[.

### zero args: [ ]
[ ] || echo false
# stdout: false

### one arg: [ x ] where x is one of '=' '!' '(' ']'
[ = ]
echo status=$?
[ ] ]
echo status=$?
[ '!' ]
echo status=$?
[ '(' ]
echo status=$?
# stdout-json: "status=0\nstatus=0\nstatus=0\nstatus=0\n"

### one arg: empty string is false.  Equivalent to -n.
test 'a'  && echo true
test ''   || echo false
# stdout-json: "true\nfalse\n"

### -a as unary operator (alias of -e)
# NOT IMPLEMENTED FOR OSH, but could be later.  See comment in core/id_kind.py.
[ -a / ]
echo status=$?
[ -a /nonexistent ]
echo status=$?
# stdout-json: "status=0\nstatus=1\n"
# N-I dash/osh stdout-json: "status=2\nstatus=2\n"

### two args: -z with = ! ( ]
[ -z = ]
echo status=$?
[ -z ] ]
echo status=$?
[ -z '!' ]
echo status=$?
[ -z '(' ]
echo status=$?
# stdout-json: "status=1\nstatus=1\nstatus=1\nstatus=1\n"

### three args
[ foo = '' ]
echo status=$?
[ foo -a '' ]
echo status=$?
[ foo -o '' ]
echo status=$?
[ ! -z foo ]
echo status=$?
[ \( foo \) ]
echo status=$?
# stdout-json: "status=1\nstatus=1\nstatus=0\nstatus=0\nstatus=0\n"

### four args
[ ! foo = foo ]
echo status=$?
[ \( -z foo \) ]
echo status=$?
# stdout-json: "status=1\nstatus=1\n"

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

### -n
test -n 'a'  && echo true
test -n ''   || echo false
# stdout-json: "true\nfalse\n"

### ! -a -o
[ -z '' -a ! -z x ]
echo status=$?
# stdout: status=0

### ( )
[ -z '' -a '(' ! -z x ')' ]
echo status=$?
# stdout: status=0

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

### == and = does not do glob
[ abc = 'a*' ]
echo status=$?
[ abc == 'a*' ]
echo status=$?
# stdout-json: "status=1\nstatus=1\n"
# N-I dash stdout-json: "status=1\nstatus=2\n"

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

### [ '(' foo ] is runtime syntax error
[ '(' foo ]
echo status=$?
# stdout: status=2

### -z '>' implies two token lookahead
[ -z ] && echo true  # -z is operand
[ -z '>' ] || echo false  # -z is operator
[ -z '>' -- ] && echo true  # -z is operand
# stdout-json: "true\nfalse\ntrue\n"

### operator/operand ambiguity with ]
# bash parses this as '-z' AND ']', which is true.  It's a syntax error in
# dash/mksh.
[ -z -a ] ]
echo status=$?
# stdout: status=0
# OK mksh stdout: status=2
# OK dash stdout: status=2

### operator/operand ambiguity with -a
# bash parses it as '-z' AND '-a'.  It's a syntax error in mksh but somehow a
# runtime error in dash.
[ -z -a -a ]
echo status=$?
# stdout: status=0
# OK mksh stdout: status=2
# OK dash stdout: status=1

### -d
test -d $TMP
echo status=$?
test -d $TMP/__nonexistent_Z_Z__
echo status=$?
# stdout-json: "status=0\nstatus=1\n"
