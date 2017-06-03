#!/bin/bash
#
# Test set flags, sh flags.

### can continue after unknown option
# dash and mksh make this a fatal error no matter what.
set -o errexit
set -o STRICT || true # unknown option
echo hello
# stdout: hello
# BUG dash/mksh stdout-json: ""

### nounset
echo "[$unset]"
set -o nounset
echo "[$unset]"
echo end  # never reached
# stdout: []
# status: 1
# OK dash status: 2

### -u is nounset
echo "[$unset]"
set -u
echo "[$unset]"
echo end  # never reached
# stdout: []
# status: 1
# OK dash status: 2

### reset option with long flag
set -o errexit
set +o errexit
echo "[$unset]"
# stdout: []
# status: 0

### reset option with short flag
set -u 
set +u
echo "[$unset]"
# stdout: []
# status: 0

### sh -c
$SH -c 'echo hi'
# stdout: hi
# status: 0

### -n for no execution (useful with --ast-output)
# NOTE: set +n doesn't work because nothing is executed!
echo 1
set -n
echo 2
set +n
echo 3
# stdout-json: "1\n"
# status: 0

### xtrace
echo 1
set -o xtrace
echo 2
# stdout-json: "1\n2\n"
# stderr: + echo 2

### errexit aborts early
set -o errexit
echo hi | grep nonexistent
echo two
# stdout-json: ""
# status: 1

### errexit with { }
# This aborts because it's not part of an if statement.
set -o errexit
{ echo one; false; echo two; }
# stdout: one
# status: 1

### errexit with if and { }
set -o errexit
if { echo one; false; echo two; }; then
  echo three
fi
echo four
# stdout-json: "one\ntwo\nthree\nfour\n"
# status: 0

### errexit with ||
set -o errexit
echo hi | grep nonexistent || echo ok
# stdout: ok
# status: 0

### errexit with &&
set -o errexit
echo ok && echo hi | grep nonexistent 
# stdout: ok
# status: 1

### errexit with !
set -o errexit
echo one
! true
echo two
! false
echo three
# stdout-json: "one\ntwo\nthree\n"
# status: 0

### errexit with while/until
set -o errexit
while false; do
  echo ok
done
until false; do
  echo ok  # do this once then exit loop
  break
done
# stdout: ok
# status: 0

### errexit with (( ))
# from http://mywiki.wooledge.org/BashFAQ/105, this changed between verisons.
set -o errexit
i=0
(( i++ ))
echo done
# stdout-json: ""
# status: 1
# N-I dash status: 127
# N-I dash stdout-json: ""

### errexit with subshell
set -o errexit
( echo one; false; echo two; )
# stdout: one
# status: 1

### errexit with command sub
# This is the bug here:
# https://blogs.janestreet.com/when-bash-scripts-bite/
set -o errexit
s=$(echo one; false; echo two;)
echo "$s"
# stdout-json: "one\n"
# status: 0
# BUG bash stdout-json: "one\ntwo\n"
# BUG dash/mksh stdout-json: ""
# BUG dash/mksh status: 1

### errexit with local
# I've run into this problem a lot.
# https://blogs.janestreet.com/when-bash-scripts-bite/
set -o errexit
f() {
  echo good
  local x=$(echo bad; false)
  echo $x
}
f
# stdout-json: "good"
# status: 1
# BUG bash/dash/mksh stdout-json: "good\nbad\n"
# BUG bash/dash/mksh status: 0

### setting errexit while it's being ignored
# ignored and then set again
if { echo 1; false; echo 2; set -o errexit; echo 3; false; echo 4; }; then
  echo 5;
fi
echo 6
false  # this is the one that makes it fail!
       # TODO: might want to disallow setting errexit while it's ignored?
       # That means it goes at the top of the script.
echo 7
# stdout-json: "1\n2\n3\n4\n5\n6\n"
# status: 1

### setting errexit in a subshell works but doesn't affect parent shell
( echo 1; false; echo 2; set -o errexit; echo 3; false; echo 4; )
echo 5
false
echo 6
# stdout-json: "1\n2\n3\n5\n6\n"
# status: 0

### setting errexit while it's being ignored in a subshell
if ( echo 1; false; echo 2; set -o errexit; echo 3; false; echo 4 ); then
  echo 5;
fi
echo 6
false 
echo 7
# stdout-json: "1\n2\n3\n4\n5\n6\n7\n"
# status: 0
