#!/usr/bin/env bash

### exec builtin 
exec echo hi
# stdout: hi

### exec builtin with redirects
exec 1>&2
echo 'to stderr'
# stdout-json: ""
# stderr: to stderr

### exec builtin with here doc
# This has in a separate file because both code and data can be read from
# stdin.
$SH spec/builtins-exec-here-doc-helper.sh
# stdout-json: "x=one\ny=two\nDONE\n"

### cd and $PWD
cd /
echo $PWD
# stdout: /

### $OLDPWD
cd /
cd $TMP
echo "old: $OLDPWD"
cd -
# stdout-json: "old: /\n/\n"

### pwd
cd /
pwd
# stdout: /

### pwd -P
mkdir -p $TMP/symtarg
ln -s $TMP/symtarg $TMP/symlink
cd $TMP/symlink
basename $(pwd -P)
cd $TMP
rmdir $TMP/symtarg
rm $TMP/symlink
# stdout: symtarg

### cd with no arguments
HOME=$TMP/home
mkdir -p $HOME
cd
test $(pwd) = "$HOME" && echo OK
# stdout: OK

### cd to nonexistent dir
cd /nonexistent/dir
echo status=$?
# stdout: status=1
# OK dash/mksh stdout: status=2

### cd away from dir that was deleted
dir=$TMP/cd-nonexistent
mkdir -p $dir
cd $dir
rmdir $dir
cd $TMP
echo $(basename $OLDPWD)
echo status=$?
## STDOUT:
cd-nonexistent
status=0
## END

### cd permits double bare dash
cd -- /
echo $PWD
# stdout: /

### cd to non-symlink with -P
targ=$TMP/cd-symtarget
lnk=$TMP/cd-symlink
mkdir -p $targ
ln -s $targ $lnk
cd -P $targ
test $PWD = "$TMP/cd-symtarget" && echo OK
cd $TMP
rmdir $targ
rm $lnk
# stdout: OK

### cd to symlink default behavior
targ=$TMP/cd-symtarget
lnk=$TMP/cd-symlink
mkdir -p $targ
ln -s $targ $lnk
cd $lnk
test $PWD = "$TMP/cd-symlink" && echo OK
cd $TMP
rmdir $targ
rm $lnk
# stdout: OK

### cd to symlink with -L
targ=$TMP/cd-symtarget
lnk=$TMP/cd-symlink
mkdir -p $targ
ln -s $targ $lnk
cd -L $lnk
test $PWD = "$TMP/cd-symlink" && echo OK
cd $TMP
rmdir $targ
rm $lnk
# stdout: OK

### cd to symlink with -P
targ=$TMP/cd-symtarget
lnk=$TMP/cd-symlink
mkdir -p $targ
ln -s $targ $lnk
cd -P $lnk
test $PWD = "$TMP/cd-symtarget" && echo OK
cd $TMP
rmdir $targ
rm $lnk
# stdout: OK

### pushd/popd
set -o errexit
cd /
pushd $TMP
popd
pwd
# status: 0
# N-I dash/mksh status: 127

### Eval
eval "a=3"
echo $a
# stdout: 3

### Source
lib=$TMP/spec-test-lib.sh
echo 'LIBVAR=libvar' > $lib
. $lib  # dash doesn't have source
echo $LIBVAR
# stdout: libvar

### Source nonexistent
source /nonexistent/path
echo status=$?
# stdout: status=1
# OK dash stdout: status=127

### Source with no arguments
source
echo status=$?
# stdout: status=1
# OK bash stdout: status=2
# OK dash stdout: status=127

### Source with extra arguments
lib=$TMP/to-be-sourced
echo 'echo $@' > $lib
. $lib foo bar  # dash doesn't have source
# stdout: foo bar
# N-I dash stdout:

### Source from inside function
lib=$TMP/to-be-sourced
echo 'echo $@' > $lib
echo 'local foo=foo_val' >> $lib
f() { . $lib; . $lib args to src; echo $foo; }
f args to func
## STDOUT:
args to func
args to src
foo_val
## END
## N-I dash STDOUT:
args to func
args to func
foo_val
## END

### Nested function arguments
f() { echo $@; }
g() { f $@; }
h() { f; }
g foo bar
h foo bar
## stdout-json: "foo bar\n\n"

### Exit out of function
f() { exit 3; }
f
exit 4
# status: 3

### Exit builtin with invalid arg 
exit invalid
# Rationale: runtime errors are 1
# status: 1
# OK dash/bash status: 2

### Exit builtin with too many args
# This is a parse error in OSH.
exit 7 8 9
echo status=$?
# status: 2
# stdout-json: ""
# BUG bash status: 0
# BUG bash stdout: status=1
# BUG dash status: 7
# BUG dash stdout-json: ""
# OK mksh status: 1
# OK mksh stdout-json: ""

### time block
# bash and mksh work; dash does't.
# TODO: osh needs to implement BraceGroup redirect properly.
err=_tmp/time-$(basename $SH).txt
{
  time {
    sleep 0.01
    sleep 0.02
  }
} 2> $err
cat $err | grep --only-matching real
# Just check that we found 'real'.
# This is fiddly:
# | sed -n -E -e 's/.*(0m0\.03).*/\1/'
#
# status: 0
# stdout: real
# BUG dash status: 2
# BUG dash stdout-json: ""

### time pipeline
time echo hi | wc -c
# stdout: 3
# status: 0

### shift
set -- 1 2 3 4
shift
echo "$@"
shift 2
echo "$@"
# stdout-json: "2 3 4\n4\n"
# status: 0

### Shifting too far
set -- 1
shift 2
# status: 1
# OK dash status: 2

### Invalid shift argument
shift ZZZ
# status: 1
# OK dash status: 2
# BUG mksh status: 0

### get umask
umask | grep '[0-9]\+'  # check for digits
# status: 0

### set umask in octal
rm $TMP/umask-one $TMP/umask-two
umask 0002
echo one > $TMP/umask-one
umask 0022
echo two > $TMP/umask-two
stat -c '%a' $TMP/umask-one $TMP/umask-two
# status: 0
# stdout-json: "664\n644\n"
# stderr-json: ""

### set umask symbolically
umask 0002  # begin in a known state for the test
rm $TMP/umask-one $TMP/umask-two
echo one > $TMP/umask-one
umask g-w,o-w
echo two > $TMP/umask-two
stat -c '%a' $TMP/umask-one $TMP/umask-two
# status: 0
## STDOUT:
664
644
## END
## stderr-json: ""
