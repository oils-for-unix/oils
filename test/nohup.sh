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

: ${LIB_OSH=stdlib/osh}
source $LIB_OSH/bash-strict.sh
source $LIB_OSH/task-five.sh

source test/common.sh  # run-test-funcs

run-shell() {
  local sh=$1
  shift

  rm -v nohup.out || true

  set +o errexit
  nohup $sh "$@"
  echo "  => $sh returned $?"
  set -o errexit

  if test -f nohup.out; then
    cat nohup.out
  else
    # happens in CI ?  I thought we run with docker -t.
    echo "nohup.out doesn't exist"
  fi

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

  run-shell bin/osh -c 'json read'
}

# TODO: Use byo-server
soil-run() {
  # Make sure there's a TTY
  echo TTY
  tty
  echo

  # Somehow it behaves differently in CI
  nohup --version
  echo

  # Can't use run-test-funcs because it "steals" input from stdin
  # run-test-funcs
  for t in test-echo test-read test-json-read; do
    echo 
    echo "*** Running $t"
    echo

    $0 $t < $(tty)

  done
}

task-five "$@"
