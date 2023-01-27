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
source test/osh2oil.sh  # common functions

#
# UNCHANGED
#

test-simple-command() {
  ### Unchanged

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo hi
OSH
echo hi
OIL
}


test-line-breaks() {
  ### Unchanged

  osh0-oil3 << 'OSH' 3<< 'OIL'
echo one \
  two three \
  four
OSH
echo one \
  two three \
  four
OIL
}

test-and-or() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
ls && echo "$@" || die "foo"
OSH
ls && echo @ARGV || die "foo"
OIL
}

#
# CHANGED
#

test-dollar-at() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
echo one "$@" two
OSH
echo one @ARGV two
OIL
}

test-bracket-builtin() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
[ ! -z "$foo" ] || die
OSH
test ! -z $foo || die
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
if [ "$foo" -eq 3 ]; then
  echo yes
fi
OSH
if test $foo -eq 3 {
  echo yes
}
OIL
}

test-while-loop() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
while read line; do
  echo $line
done
OSH
while read line {
  echo $line
}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
while read \
  line; do
  echo $line
done
OSH
while read \
  line {
  echo $line
}
OIL
}

test-if() {
  osh0-oil3 << 'OSH' 3<< 'OIL'
if true; then
  echo yes
fi
OSH
if true {
  echo yes
}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
if true
then
  echo yes
fi
OSH
if true
{
  echo yes
}
OIL

  osh0-oil3 << 'OSH' 3<< 'OIL'
if true; then
  echo yes
elif false; then
  echo elif
elif spam; then
  echo elif
else
  echo no
fi
OSH
if true {
  echo yes
} elif false {
  echo elif
} elif spam {
  echo elif
} else {
  echo no
}
OIL
}



soil-run() {
  run-test-funcs
}

"$@"
