#!/usr/bin/env bash

### echo dashes
echo -
echo --
echo ---
# stdout-json: "-\n--\n---\n"

### echo -en
echo -en 'abc\ndef\n'
# stdout-json: "abc\ndef\n"
# N-I dash stdout-json: "-en abc\ndef\n\n"

### echo -ez (invalid flag)
# bash differs from the other two shells, but its behavior is possibly more
# sensible, if you're going to ignore the error.  It doesn't make sense for the
# 'e' to mean 2 different things simultaneously: flag and literal to be
# printed.
echo -ez 'abc\n'
# stdout-json: "-ez abc\\n\n"
# BUG dash/mksh stdout-json: "-ez abc\n\n"

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
$SH spec/exec-here-doc.sh
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

### pushd/popd
set -o errexit
cd /
pushd $TMP
popd
pwd
# status: 0
# N-I dash/mksh status: 127

### Source
lib=$TMP/spec-test-lib.sh
echo 'LIBVAR=libvar' > $lib
. $lib  # dash doesn't have source
echo $LIBVAR
# stdout: libvar

### Exit builtin
exit 3
# status: 3

### Exit builtin with invalid arg 
exit invalid
# Rationale: runtime errors are 1
# status: 1
# OK dash/bash status: 2

### Exit builtin with too many args
exit 7 8 9
echo "no exit: $?"
# status: 0
# stdout-json: "no exit: 1\n"
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

### Read builtin
# NOTE: there are TABS below
read x <<EOF
A		B C D E
FG
EOF
echo "[$x]"
# stdout: [A		B C D E]
# status: 0

### Read builtin with no newline.
# This is odd because the variable is populated successfully.  OSH/Oil might
# need a separate put reading feature that doesn't use IFS.
echo -n ZZZ | { read x; echo $?; echo $x; }
# stdout-json: "1\nZZZ\n"
# status: 0

### Read builtin with multiple variables
# NOTE: there are TABS below
read x y z <<EOF
A		B C D E
FG
EOF
echo "$x/$y/$z"
# stdout: A/B/C D E
# status: 0

### Read builtin with not enough variables
set -o errexit
set -o nounset  # hm this doesn't change it
read x y z <<EOF
A B
EOF
echo /$x/$y/$z/
# stdout: /A/B//
# status: 0

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
rm $TMP/umask-one $TMP/umask-two
echo one > $TMP/umask-one
umask g-w,o-w
echo two > $TMP/umask-two
stat -c '%a' $TMP/umask-one $TMP/umask-two
# status: 0
# stdout-json: "664\n644\n"
# stderr-json: ""

