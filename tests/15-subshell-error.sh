#!/bin/bash

set -o errexit

# Problem: A WORD cannot fail.  Only a COMMAND can fail.

# http://stackoverflow.com/questions/29532904/bash-subshell-errexit-semantics
# https://groups.google.com/forum/?fromgroups=#!topic/gnu.bash.bug/NCK_0GmIv2M

# http://unix.stackexchange.com/questions/23026/how-can-i-get-bash-to-exit-on-backtick-failure-in-a-similar-way-to-pipefail

echo $(echo hi > "$@")
echo 'should not reach here'
echo

# OK this one works.  Because the exit code of the assignment is the exit
# code of the RHS?
foo=$(echo hi > "$@")
echo $foo
echo 'should not reach here 2'
