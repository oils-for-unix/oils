#!/bin/bash
#
# Usage:
#   ./time-test.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source test/common.sh

time-tool() {
  $(dirname $0)/time_.py "$@"
}

test-tsv() {
  local out=_tmp/time.tsv
  rm -f $out

  for i in 1 2 3; do
    time-tool --tsv -o $out -- sleep 0.0${i}
  done
  cat $out
}

test-append() {
  local out=_tmp/overwrite.tsv
  for i in 4 5; do
    time-tool --tsv -o $out -- sleep 0.0${i}
  done
  local num_lines=$(cat $out | wc -l)
  test $num_lines -eq 1 || fail "Expected 1 line, got $num_lines"

  local out=_tmp/append.tsv
  for i in 4 5; do
    time-tool --tsv -o $out --append -- sleep 0.0${i}
  done
  wc -l $out
}

test-usage() {
  # no args
  set +o errexit

  time-tool; status=$?
  test $status = 2 || fail "Unexpected status $status"
  time-tool --output; status=$?
  test $status = 2 || fail "Unexpected status $status"

  time-tool sleep 0.1
  time-tool --append sleep 0.1; status=$?
  test $status = 0 || fail "Unexpected status $status"

  set -o errexit
}

test-cannot-serialize() {
  local out=_tmp/time2.tsv
  rm -f $out

  set +o errexit

  # Newline should fail
  time-tool --tsv -o $out --field $'\n' -- sleep 0.001; status=$?
  test $status = 1 || fail "Unexpected status $status"

  # Tab should fail
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
  test-usage
  test-tsv
  test-append
  test-cannot-serialize

  echo
  echo "All tests in $0 passed."
}

"$@"
