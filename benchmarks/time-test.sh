#!/bin/bash
#
# Usage:
#   ./time-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

time-tool() {
  $(dirname $0)/time.py "$@"
}

test-tsv() {
  local out=_tmp/time.tsv
  rm -f $out

  for i in 1 2 3; do
    time-tool --tsv -o $out -- sleep 0.0${i}
  done
  cat $out
}

test-cannot-serialize() {
  local out=_tmp/time2.tsv
  rm -f $out

  set +o errexit

  # Tab should fail
  time-tool --tsv -o $out --field $'\n' -- sleep 0.001; status=$?
  test $status = 1 || fail "Unexpected status $status"

  # Newline should fail
  time-tool --tsv -o $out --field $'\t' -- sleep 0.001; status=$?
  test $status = 1 || fail "Unexpected status $status"

  # Quote should fail
  time-tool --tsv -o $out --field '"' -- sleep 0.001; status=$?
  test $status = 1 || fail "Unexpected status $status"

  # Backslash is OK
  time-tool --tsv -o $out --field '\' -- sleep 0.001; status=$?
  test $status = 0 || fail "Unexpected status $status"

  # Space is OK, although canonical form would be " "
  time-tool --tsv -o $out --field ' ' -- sleep 0.001; status=$?
  test $status = 0 || fail "Unexpected status $status"

  set -o errexit

  cat $out
}

all-passing() {
  test-tsv
  test-cannot-serialize

  echo
  echo "All tests in $0 passed."
}

"$@"
