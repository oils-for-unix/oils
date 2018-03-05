#!/bin/bash
#
# Usage:
#   ./oshc-deps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

# TODO: We need a common test framework for command-line syntax of bin/*.  The
# spec tests are doing that now with $SH.
# osh2oil should be oshc translate.

# Compare osh code on stdin (fd 0) and expected oil code on fd 3.
assert-deps() {
  bin/oshc deps | diff -u /dev/fd/3 - || fail
}

usage() {
  set +o errexit

  # missing required subcommand
  bin/oshc
  test $? -eq 2 || fail

  bin/oshc invalid
  test $? -eq 2 || fail

  # Syntax error
  echo '<' | bin/oshc deps 
  test $? -eq 2 || fail

  # File not found
  bin/oshc deps nonexistent.txt
  test $? -eq 2 || fail

  return

  # Doesn't work yet
  echo --
  bin/oshc --help
  test $? -eq 0 || fail

  set -o errexit
}

deps() {
  bin/oshc deps $0
  test $? -eq 0 || fail

  # Have to go inside a condition
  assert-deps <<EOF 3<<DEPS
if { grep foo bar; } then
  cat hi
fi
EOF
grep
cat
DEPS

  # g is used textually before defined, but that's OK
  assert-deps <<EOF 3<<DEPS
f() {
  g
}
g() {
  echo G
}
f
grep foo bar
EOF
grep
DEPS

  # g is used before defined, NOT OK
  assert-deps <<EOF 3<<DEPS
g
g() {
  echo G
}
grep foo bar
EOF
g
grep
DEPS
}

readonly -a PASSING=(
  usage
  deps
)

all-passing() {
  run-all "${PASSING[@]}"
}

"$@"
