#!/usr/bin/env bash
#
# Wrapper for test/interactive.py
#
# Usage:
#   test/interactive.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

soil-run() {
  # Run it a few times to test flakiness

  local n=5
  echo "Running $n times"

  # In the CI image we run as root :-(
  # We don't want 'root# ' as the prompt!

  export PS1='test-sh$ '

  local num_success=0
  local status=0

  for i in $(seq $n); do
    echo -----
    echo "Iteration $i"
    echo -----

    set +o errexit
    test/interactive.py
    status=$?
    set -o errexit

    if test "$status" -eq 0; then
      num_success=$((num_success + 1))
    fi
  done

  # This test is flaky, so only require 2 of 5 successes
  echo "test/interactive: $num_success of $n tries succeeded"

  if test "$num_success" -ge 2; then
    return 0
  else
    return 1
  fi
}

"$@"
