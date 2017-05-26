#!/bin/bash

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

### Export sets a global variable
# Even after you do export -n, it still exists.
f() { export GLOBAL=X; }
f
echo $GLOBAL
printenv.py GLOBAL
# stdout-json: "X\nX\n"

### Export sets a global variable that persists after export -n
f() { export GLOBAL=X; }
f
echo $GLOBAL
printenv.py GLOBAL
export -n GLOBAL
echo $GLOBAL
printenv.py GLOBAL
# stdout-json: "X\nX\nX\nNone\n"
# N-I mksh/dash stdout-json: "X\nX\n"

### Export a global variable and unset it
f() { export GLOBAL=X; }
f
echo $GLOBAL
printenv.py GLOBAL
unset GLOBAL
echo $GLOBAL
printenv.py GLOBAL
# stdout-json: "X\nX\n\nNone\n"

### Export existing global variables
G1=g1
G2=g2
export G1 G2
printenv.py G1 G2
# stdout-json: "g1\ng2\n"

### Export existing local variable
f() {
  local L1=local1
  export L1
  printenv.py L1
}
f
printenv.py L1
# stdout-json: "local1\nNone\n"

### Export a local that shadows a global
V=global
f() {
  local V=local1
  export V
  printenv.py V
}
f
printenv.py V  # exported local out of scope; global isn't exported yet
export V
printenv.py V  # now it's exported
# stdout-json: "local1\nNone\nglobal\n"

### Export a variable before defining it
export U
U=u
printenv.py U
# stdout: u

### Exporting a parent func variable (dynamic scope)
# The algorithm is to walk up the stack and export that one.
inner() {
  export outer_var
  echo "inner: $outer_var"
  printenv.py outer_var
}
outer() {
  local outer_var=X
  echo "before inner"
  printenv.py outer_var
  inner
  echo "after inner"
  printenv.py outer_var
}
outer
# stdout-json: "before inner\nNone\ninner: X\nX\nafter inner\nX\n"

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
