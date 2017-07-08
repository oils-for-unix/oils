#!/usr/bin/env bash
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

# Hm this is behavior is odd.  Usually errexit stops at first failed command.
# || suppresses this functions and blocks!
#
# I guess it is sort of like "if { grep foo; grep bar } ?

test-func-or() {
  _func || echo "Test function FAILED"
  
  echo DONE  # We get here
}

test-brace-or() {
  { fail
    ok
  } || {
    echo "Test block FAILED"
  }

  echo DONE
}

test-func-if() {
  if _func; then
    echo THEN  # shouldn't succeed!
  else
    echo ELSE
  fi

  echo DONE
}

test-brace-if() {
  if { fail; ok; }; then
    echo THEN  # shouldn't succeed!
  else
    echo ELSE
  fi

  echo DONE
}

# This behaves as expected
test-func-pipe() {
  _func | tee /dev/null
  echo PIPE
}

test-brace-pipe() {
  { fail; ok; } | tee /dev/null
  echo PIPE
}

# We get ELSE
test-fail-if() {
  if fail; then
    echo THEN
  else
    echo ELSE
  fi

  echo DONE
}

# We get ELSE
test-fail-or() {
  fail || echo FAILED

  echo DONE
}

"$@"
