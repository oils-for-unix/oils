#!/bin/bash
#
# Usage:
#   ./osh-to-oil-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit


osh-to-oil() {
  bin/osh --no-exec --fix "$@"
}

fail() {
  echo 'TEST FAILED'
  exit 1
}

# Compare osh code on stdin (fd 0) and expected oil code on fd 3.
osh0-oil3() {
  osh-to-oil "$@" | diff -u /dev/fd/3 - || fail
}

simple-command() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo hi
OSH
echo hi
OIL
}

redirect() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
cat >out.txt <in.txt
OSH
cat >out.txt <in.txt
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
cat >out.txt 2> err.txt
OSH
cat >out.txt !2 > err.txt
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo "error message" >& 2 
OSH
echo "error message" > !2 
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo "error message" 1>&2 
OSH
echo "error message" !1 > !2 
OIL
}

here-doc() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
cat <<ONE
echo $hi
ONE
OSH
cat << """
echo $hi
"""
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
cat <<'ONE'
single quoted
ONE
OSH
cat << '''
single quoted
'''
OIL

  # TODO: <<-
}

pipeline() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
ls | sort | uniq -c | sort -n -r
OSH
ls | sort | uniq -c | sort -n -r
OIL
}

and-or() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
ls && echo || die "foo"
OSH
ls && echo || die "foo"
OIL
}

posix-func() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
func1() {
  echo func1
  func2()
  {
    echo func2
  }
}
OSH
proc func1 {
  echo func1
  proc func2
  {
    echo func2
  }
}
OIL
}

subshell-func() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
subshell-func() (
  echo subshell
)
OSH
proc subshell-func {
  shell { 
    echo subshell
  }
}
OIL
}

ksh-func() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
function func1 {  # no parens
  echo func1
  function func2()
  {
    echo func2
  }
}
OSH
proc func1 {  # no parens
  echo func1
  proc func2
  {
    echo func2
  }
}
OIL
}

for-loop() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
for x in a b c \
  d e f; do
  echo $x
done
OSH
for x in [a b c \
  d e f] {
  echo $x
}
OIL
}

while-loop() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
while read line; do
  echo $line
done
OSH
while read line {
  echo $line
}
OIL
}

subshell() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
(echo hi)
done
OSH
shell {echo hi}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
(echo hi; echo bye)
done
OSH
shell {echo hi; echo bye}
OIL
}

fork() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
sleep 1&
OSH
fork sleep 1
OIL
}

empty-for-loop() {
  for x in 
  do
    echo $x
  done
}

args-for-loop() {
  set -- 1 2 3
  for x
  do
    echo $x
  done
}

var-sub() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $foo
OSH
echo $foo
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $foo ${bar} "__${bar}__"
OSH
echo $foo $(bar) "__$(bar)__"
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo ${foo:-default}
OSH
echo $(foo or 'default')
OIL
}

command-sub() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $(echo hi)
echo `echo hi`
OSH
echo $[echo hi]
echo $[echo hi]
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo "__$(echo hi)__"
OSH
echo "__$[echo hi]__"
OIL
}

arith-sub() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo __$((  1+ 2 ))__
OSH
echo __$(  1+ 2 )__
OIL
  return

  # Non-standard Bash style
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $[  1+ 2 ]
OSH
echo $(  1+ 2 )
OIL

}

all-passing() {
  simple-command
  redirect
  pipeline
  and-or
  posix-func
  ksh-func
  command-sub
  arith-sub
}

"$@"
