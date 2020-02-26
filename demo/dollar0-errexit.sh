#!/bin/bash
#
# Pattern for testing if a function has succeeded or failed with set -e:
#
#    SUMMARY: Call it through $0.
# 
# Useful for test frameworks!
#
# Usage:
#   demo/dollar0-errexit.sh <function name>

set -o nounset
set -o pipefail
set -o errexit

# Should produce TWO lines, not THREE.
# And the whole thing FAILS with exit code 1.
myfunc() {
  echo one
  echo two
  false      # should FAIL here
  echo three
}

mypipeline() { myfunc | wc -l; }

# Prints three lines because errexit is implicitly disabled.
# It also shouldn't succeed.
bad() {
  if myfunc | wc -l; then
    echo true
  else
    echo false
  fi
  echo status=$?
}

# This fixes the behavior.  Prints two lines and fails.
good() {
  if $0 mypipeline; then
    echo true
  else
    echo false
  fi
  echo status=$?
}

# This is pretty much what 'bad' is dong.
not-a-fix() {
  set +o errexit
  mypipeline
  local status=$?
  set -o errexit

  if test $? -eq 0; then
    echo true
  else
    echo false
  fi
  echo status=$?
}

"$@"
