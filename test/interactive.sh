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

  for i in $(seq $n); do
    echo -----
    echo "Iteration $i"
    echo -----

    test/interactive.py
  done
}

"$@"
