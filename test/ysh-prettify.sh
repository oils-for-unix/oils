#!/usr/bin/env bash
#
# Test ysh-prettify transformations
#
# Usage:
#   ./ysh-prettify.sh <function name>
#
# TODO:
#
# - Validate before and after
#   osh -n $OLD_CODE
#   ysh -n $OLD_CODE
#
# - Get rid of here docs, because they break syntax highlighting

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

soil-run() {
  run-test-funcs
}

"$@"
