#!/usr/bin/env bash
#
# Test ysh-prettify transformations
#
# Usage:
#   ./ysh-prettify.sh <function name>

set -o nounset
set -o pipefail
set -o errexit
shopt -s strict:all 2>/dev/null || true  # dogfood for OSH

source test/common.sh

readonly TEMP_DIR=_tmp

check-osh2ysh() {
  local osh_str=$1
  local ysh_str=$2  # expected

  # Make sure they are valid

  bin/osh -n -c "$osh_str"
  bin/ysh -n -c "$ysh_str"

  local tmp=$TEMP_DIR/actual.ysh
  echo "$osh_str" | bin/oshc translate | tee $tmp

  echo "$ysh_str" | diff -u $tmp -
  echo 'OK'
}

#
# UNCHANGED
#

test-simple-command() {
  ### Unchanged

  check-osh2ysh 'echo hi' 'echo hi'
}


test-line-breaks() {
  ### Unchanged

  check-osh2ysh '
echo one \
  two three \
  four
' '
echo one \
  two three \
  four
'
}

test-and-or() {
  check-osh2ysh \
    'ls && echo "$@" || die "foo"' \
    'ls && echo @ARGV || die "foo"'
}

#
# CHANGED
#

test-dollar-at() {
  check-osh2ysh \
    'echo one "$@" two' \
    'echo one @ARGV two'
}

test-bracket-builtin() {
  check-osh2ysh \
    '[ ! -z "$foo" ] || die' \
    'test ! -z $foo || die'

  check-osh2ysh '
if [ "$foo" -eq 3 ]; then
  echo yes
fi' \
  '
if test $foo -eq 3 {
  echo yes
}'
}

test-while-loop() {
  check-osh2ysh '
while read line; do
  echo $line
done' \
  '
while read line {
  echo $line
}'

  check-osh2ysh '
while read \
  line; do
  echo $line
done' \
  '
while read \
  line {
  echo $line
}'
}

test-if() {
  check-osh2ysh '
if true; then
  echo yes
fi' \
  '
if true {
  echo yes
}'

  check-osh2ysh '
if true; then
  echo yes
elif false; then
  echo elif
elif spam; then
  echo elif
else
  echo no
fi' \
  '
if true {
  echo yes
} elif false {
  echo elif
} elif spam {
  echo elif
} else {
  echo no
}'
}

# TODO: Fix this

TODO-test-then-next-line() {
  check-osh2ysh '
if true
then
  echo yes
fi' \
  '
if true {
  echo yes
}'

}

source test/osh2oil.sh

TODO-test-prefix-ops() {
  check-osh2ysh \
    'echo ${#s} ${#a[@]}' \
    'echo $[len(s)] $[len(a)]'
}

TODO-test-unquote-subs() {
  check-osh2ysh \
    'echo "$1" "$foo"' \
    'echo $1 $foo'

  # TODO: $foo and $(echo hi)

  check-osh2ysh \
    'echo "${foo}"' \
    'echo $(foo)' \

  check-osh2ysh \
    'echo "$(echo hi)"' \
    'echo $[echo hi]'
}

# Downgraded to one_pass_parse.  This means \" will be wrong, but meh.
# Here the WordParser makes another pass with CommandParser.
#
# We could also translate it to:
#   echo $[compat backticks 'echo hi']
# But that might be overly pedantic.  This will work most of the time.

TODO-test-backticks() {

  # Make this pass
  check-osh2ysh \
   'echo `echo hi ${var}`' \
   'echo $[echo hi $(var)]'

  # These also have problems
  check-osh2ysh \
    'echo `{ echo hi; }`' \
    'echo $[do { echo hi }]'

  check-osh2ysh \
    'echo $({ echo hi; })' \
    'echo $[do { echo hi }]'
}


test-source-builtin() {
  check-osh2ysh \
    '. lib.sh' \
    'source lib.sh'

  check-osh2ysh \
    '[ -f lib.sh ] && . lib.sh' \
    'test -f lib.sh && source lib.sh'
}

TODO-test-set-builtin() {
  # Not needed now that we have 'setvar' ?

  osh0-oil3 << 'OSH' 3<< 'OIL'
set -o errexit
OSH
shopt --set errexit
OIL
}

test-posix-func() {
  check-osh2ysh '
  f() {
    echo "hi"
  }' '
  proc f {
    echo "hi"
  }'

  return

  # TODO: Move the brace
  check-osh2ysh '
  f()
  {
    echo "hi"
  }' '
  proc f
  {
    echo "hi"
  }'

  # No nested functinos
  return
  check-osh2ysh '
func1() {
  echo func1
  func2()
  {
    echo func2
  }
}' \
  '
proc func1 {
  echo func1
  proc func2
  {
    echo func2
  }
}'

}

test-ksh-func() {
  check-osh2ysh '
function func1 {  # no parens
  echo func1
}' '
proc func1 {  # no parens
  echo func1
}'
}

test-for-loop() {
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

  osh0-oil3 << 'OSH' 3<< 'OIL'
for x in a b c \
  d e f
do
  echo $x
done
OSH
for x in [a b c \
  d e f]
{
  echo $x
}
OIL
}

test-empty-for-loop() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
for x in 
do
  echo $x
done
OSH
for x in []
{
  echo $x
}
OIL
}

test-args-for-loop() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
for x; do
  echo $x
done
OSH
for x in @ARGV {
  echo $x
}
OIL

  # NOTE: we don't have the detailed spid info to preserve the brace style.
  # Leave it to the reformatter?
  return

#set -- 1 2 3
#setargv -- 1 2 3
  osh0-oil3 << 'OSH' 3<< 'OIL'
for x
do
  echo $x
done
OSH
for x in @ARGV
{
  echo $x
}
OIL
}

# TODO: translate to YSTR?

TODO-test-word-joining() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo 'foo'"'" 
OSH
echo c'foo\''
OIL
}

test-command-sub() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo $(echo hi)
OSH
echo $[echo hi]
OIL

  # In double quotes
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo "__$(echo hi)__"
OSH
echo "__$[echo hi]__"
OIL
}

TODO-test-var-sub() {
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

# TODO: Fix this!

test-subshell() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
(echo hi;)
OSH
shell {echo hi;}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
(echo hi)
OSH
shell {echo hi}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
(echo hi; echo bye)
OSH
shell {echo hi; echo bye}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
( (echo hi; echo bye ) )
OSH
shell { shell {echo hi; echo bye } }
OIL
}

test-brace-group() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
{ echo hi; }
OSH
do { echo hi; }
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
{ echo hi; echo bye; }
OSH
do { echo hi; echo bye; }
OIL
}

# TODO: Change case syntax

test-case() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
case $var in
  foo|bar)
    [ -f foo ] && echo file
    ;;
  '')
    echo empty
    ;;
  *)
    echo default
    ;;
esac
OSH
match $var {
  with foo|bar
    test -f foo && echo file
    
  with ''
    echo empty
    
  with *
    echo default
    
}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
case "$var" in
  *)
    echo foo
    echo bar  # no dsemi
esac
OSH
match $var {
  with *
    echo foo
    echo bar  # no dsemi
}
OIL
}

soil-run() {
  run-test-funcs
}

"$@"
