#!/usr/bin/env bash

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
# N-I dash stdout-json: "status=2\nstatus=2\n"

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
## STDOUT:
status=2
status=2
## END

### ] syntax errors
[
echo status=$?
test  # not a syntax error
echo status=$?
[ -n x  # missing ]
echo status=$?
[ -n x ] y  # extra arg after ]
echo status=$?
[ -n x y  # extra arg
echo status=$?
## STDOUT:
status=2
status=1
status=2
status=2
status=2
## END

### -n
test -n 'a'  && echo true
test -n ''   || echo false
# stdout-json: "true\nfalse\n"

### ! -a
[ -z '' -a ! -z x ]
echo status=$?
# stdout: status=0

### -o
[ -z x -o ! -z x ]
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

### -x
rm -f $TMP/x
echo 'echo hi' > $TMP/x
test -x $TMP/x || echo 'no'
chmod +x $TMP/x
test -x $TMP/x && echo 'yes'
test -x $TMP/__nonexistent__ || echo 'bad'
# stdout-json: "no\nyes\nbad\n"

### -r
echo '1' > $TMP/testr_yes
echo '2' > $TMP/testr_no
chmod -r $TMP/testr_no  # remove read permission
test -r $TMP/testr_yes && echo 'yes'
test -r $TMP/testr_no || echo 'no'
# stdout-json: "yes\nno\n"

### -w
rm -f $TMP/testw_*
echo '1' > $TMP/testw_yes
echo '2' > $TMP/testw_no
chmod -w $TMP/testw_no  # remove write permission
test -w $TMP/testw_yes && echo 'yes'
test -w $TMP/testw_no || echo 'no'
# stdout-json: "yes\nno\n"

### -h and -L test for symlink
touch $TMP/zz
ln -s -f $TMP/zz $TMP/symlink
ln -s -f $TMP/__nonexistent_ZZ__ $TMP/dangling
test -L $TMP/zz || echo no
test -h $TMP/zz || echo no
test -f $TMP/symlink && echo is-file
test -L $TMP/symlink && echo symlink
test -h $TMP/symlink && echo symlink
test -L $TMP/dangling && echo dangling
test -h $TMP/dangling  && echo dangling
test -f $TMP/dangling  || echo 'dangling is not file'
rm $TMP/symlink  # interferes with builtins.test.sh otherwise
## STDOUT:
no
no
is-file
symlink
symlink
dangling
dangling
dangling is not file
## END

### -t 1 for stdout
# There isn't way to get a terminal in the test environment?
[ -t 1 ]
echo status=$?
## stdout: status=1

### [ -t invalid ]
[ -t invalid ]
echo status=$?
## stdout: status=2
## BUG bash stdout: status=1

### -ot and -nt
touch -d 2017/12/31 $TMP/x
touch -d 2018/01/01 > $TMP/y
test $TMP/x -ot $TMP/y && echo 'older'
test $TMP/x -nt $TMP/y || echo 'not newer'
test $TMP/x -ot $TMP/x || echo 'not older than itself'
test $TMP/x -nt $TMP/x || echo 'not newer than itself'
## STDOUT:
older
not newer
not older than itself
not newer than itself
## END
