#!/usr/bin/env bash
#
# Wrapper for test cases in spec/stateful
#
# Usage:
#   test/stateful.sh <function name>
#
# Examples:
#
#   test/stateful.sh all
#   test/stateful.sh signals -r 0-1   # run a range of tests
#   test/stateful.sh signals --list   # list tests

set -o nounset
set -o pipefail
set -o errexit

export PYTHONPATH=.

readonly OSH=bin/osh

# This uses ../oil_DEPS/spec-bin/{bash,dash} if they exist
source build/dev-shell.sh

# Use system shells until the Soil CI container has spec-bin

# The ovm-tarball container that has spec-bin doesn't have python3 :-(  Really
# we should build another container
readonly BASH=bash
readonly DASH=dash

run() {
  ### Wrapper for PYTHONPATH

  spec/stateful/signals.py "$@"

}

signals() {
  spec/stateful/signals.py --osh-failures-allowed 1 \
    $OSH bash "$@"
}

interactive() {
  spec/stateful/interactive.py \
    $OSH bash dash "$@"
}

job-control() {
  spec/stateful/job_control.py \
    $OSH bash "$@"
}

all() {
  ### Run all tests

  # TODO: The reports for each file should be written and uploaded.
  # Can we reuse the test/spec table?

  signals
  interactive
  job-control
}

soil-run() {
  ### Run it a few times to work around flakiness

  local n=5
  echo "Running $n times"

  local num_success=0
  local status=0

  for i in $(seq $n); do
    echo -----
    echo "Iteration $i"
    echo -----

    set +o errexit

    all

    status=$?
    set -o errexit

    if test "$status" -eq 0; then
      num_success=$((num_success + 1))
    fi
    if test "$num_success" -ge 2; then
      echo "test/interactive OK: 2 of $i tries succeeded"
      return 0
    fi
  done

  # This test is flaky, so only require 2 of 5 successes
  echo "test/interactive FAIL: got $num_success successes after $n tries"
  return 1
}

"$@"
