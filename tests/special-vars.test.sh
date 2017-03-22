#!/bin/bash

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

### $-
# dash's behavior seems most sensible here?
$SH -o nounset -c 'echo $-'
# OK bash stdout: huBc
# OK dash stdout: u
# OK mksh stdout: uhc
# status: 0

### $_
# This is bash-specific.
echo hi
echo $_
# stdout-json: "hi\nhi\n"
# N-I dash/mksh stdout-json: "hi\n\n"

### PID $$
# Just test that it has decimal digits
echo $$ | egrep '[0-9]+'
# status: 0

### Background PID $!
# Just test that it has decimal digits
sleep 0.01 &
echo $! | egrep '[0-9]+'
wait
# status: 0

### $PPID
expr $0 : '.*/osh$' && exit 99  # Disabled because of spec-runner.sh issue
echo $PPID | egrep '[0-9]+'
# Disabled because of spec-runner.sh issue: bash sets it for osh
# status: 0

# NOTE: There is also $BASHPID

### $PIPESTATUS
echo hi | sh -c 'cat; exit 33' | wc -l >/dev/null
argv.py "${PIPESTATUS[@]}"
# status: 0
# stdout: ['0', '33', '0']
# N-I dash stdout-json: ""
# N-I dash status: 2

### $PWD
cd /
echo $PWD
# status: 0
# stdout: /

### $RANDOM
expr $0 : '.*/osh$' && exit 99  # Disabled because of spec-runner.sh issue
echo $RANDOM | egrep '[0-9]+'
# status: 0
# N-I dash status: 1
