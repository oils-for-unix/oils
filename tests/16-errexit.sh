#!/bin/bash
#
# Usage:
#   ./16-errexit.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

fail() {
  echo FAIL
  false
}

ok() {
  echo OK
  true
}

_func() {
  fail
  ok
}

# Hm this is behavior is odd.  || suppresses errexit failures within functions
# and blocks!  It's supposed to
test-func-or() {
  _func || echo "Test function FAILED"
}

test-brace-or() {
  { fail
    ok
  } || {
    echo "Test block FAILED"
  }
}

test-func-pipe() {
  _func | tee /dev/null
  echo PIPE
}

test-brace-pipe() {
  { fail; ok; } | tee /dev/null
  echo PIPE
}

"$@"
