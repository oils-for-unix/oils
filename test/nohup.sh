#!/usr/bin/env bash
#
# This should be a spec test, but the framework runs like
#
#    echo $code | $SH
#
# which seems to interfere with nohup.
#
# Usage:
#   test/nohup.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

source devtools/run-task.sh

run-shell() {
  local sh=$1
  shift

  rm -v nohup.out || true

  set +o errexit
  nohup $sh "$@"
  echo "  => $sh returned $?"
  set -o errexit

  cat nohup.out
  echo

}

compare-shells() {
  for sh in dash bash mksh bin/osh; do
    echo "  ----- "
    echo "  $sh"
    echo

    run-shell $sh "$@"

  done
}

test-echo() {
  compare-shells -c 'echo hi; echo status=$?'
}

# TODO: osh needs location info for this one
test-read() {
  compare-shells -c 'read x; echo status=$? x=$x'
}

test-json-read() {
  rm -v nohup.out || true

  run-shell bin/osh -c 'json read :x'
}

run-task "$@"
