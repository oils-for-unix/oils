#!/usr/bin/env bash
#
# NOTE:
# - $! is tested in background.test.sh
# - $- is tested in sh-options

### $PWD
# Just test that it has a slash for now.
echo $PWD | grep -o /
# status: 0

### $1 .. $9 are scoped, while $0 is not
func() { echo $0 $1 $2 | sed -e 's/.*sh/sh/'; }
func a b
# stdout: sh a b

### $?
echo $?  # starts out as 0
sh -c 'exit 33'
echo $?
# stdout-json: "0\n33\n"
# status: 0

### $#
set -- 1 2 3 4
echo $#
# stdout: 4
# status: 0

### $_
# This is bash-specific.
echo hi
echo $_
# stdout-json: "hi\nhi\n"
# N-I dash/mksh stdout-json: "hi\n\n"

### $$ looks like a PID
# Just test that it has decimal digits
echo $$ | egrep '[0-9]+'
# status: 0

### $$ doesn't change with subshell
# Just test that it has decimal digits
set -o errexit
die() {
  echo 1>&2 "$@"; exit 1
}
parent=$$
test -n "$parent" || die "empty PID in parent"
( child=$$
  test -n "$child" || die "empty PID in child"
  test "$parent" = "$child" || die "should be equal: $parent != $child"
)
exit 3  # make sure we got here
# stdout-json: ""
# status: 3

### $BASHPID DOES change with subshell
set -o errexit
die() {
  echo 1>&2 "$@"; exit 1
}
parent=$BASHPID
test -n "$parent" || die "empty BASHPID in parent"
( child=$BASHPID
  test -n "$child" || die "empty BASHPID in child"
  test "$parent" != "$child" || die "should not be equal: $parent = $child"
)
exit 3  # make sure we got here
# stdout-json: ""
# status: 3
# N-I dash status: 1

### Background PID $! looks like a PID
sleep 0.01 &
pid=$!
wait
echo $pid | egrep '[0-9]+' >/dev/null
echo status=$?
# stdout: status=0

### $PPID
echo $PPID | egrep '[0-9]+'
# status: 0

# NOTE: There is also $BASHPID

### $PIPESTATUS
echo hi | sh -c 'cat; exit 33' | wc -l >/dev/null
argv.py "${PIPESTATUS[@]}"
# status: 0
# stdout: ['0', '33', '0']
# N-I dash stdout-json: ""
# N-I dash status: 2

### $RANDOM
expr $0 : '.*/osh$' && exit 99  # Disabled because of spec-runner.sh issue
echo $RANDOM | egrep '[0-9]+'
# status: 0
# N-I dash status: 1

### $UID and $EUID
# These are both bash-specific.
set -o errexit
echo $UID | egrep -o '[0-9]+' >/dev/null
echo $EUID | egrep -o '[0-9]+' >/dev/null
echo status=$?
# stdout: status=0
# N-I dash/mksh stdout-json: ""
# N-I dash/mksh status: 1
