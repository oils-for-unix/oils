#!/usr/bin/env bash
#
# Usage:
#   test/oshc-deps.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

# TODO: We need a common test framework for command-line syntax of bin/*.  The
# spec tests are doing that now with $SH.
# osh2oil should be oshc translate.

# Compare osh code on stdin (fd 0) and expected oil code on fd 3.
assert-deps() {
  bin/osh --tool deps | diff -u /dev/fd/3 - || fail
}

test-ourselves() {
  ### This shows an error but doesn't exit 0
  bin/osh --tool deps $0
  test $? -eq 0 || fail
}

test-deps() {
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
}

DISABLED-test-deps-2() {
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

run-for-release() {
  run-other-suite-for-release oshc-deps run-test-funcs
}

soil-run() {
  run-test-funcs
}

"$@"
