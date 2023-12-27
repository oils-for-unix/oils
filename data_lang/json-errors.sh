#!/usr/bin/env bash
#
# Usage:
#   data_lang/json-errors.sh <function name>

# NOTE: No set -o errexit, etc.

source test/common.sh  # $OSH
source test/sh-assert.sh  # banner, _assert-sh-status

# Test JSON in OSH.  Should be the same in YSH.
#OSH=${OSH:-bin/osh}

_error-case-X() {
  local expected_status=$1
  shift

  local message=$0
  _assert-sh-status $expected_status $OSH "$message" \
    -c "$@"
}

_expr-error-case() {
  ### Expect status 3
  _error-case-X 3 "$@"
}

#
# Cases
#

test-json() {
  #echo OSH=$OSH
  #set +o errexit

  _error-case-X 1 'echo { | json read'

  _error-case-X 1 'echo { | j8 read'

  #_error-case-X 3 'echo { | json read'
}

#
# Entry points
#

soil-run-py() {
  run-test-funcs
}

soil-run-cpp() {
  # This is like run-test-funcs, except errexit is off here
  ninja _bin/cxx-asan/osh
  #OSH=_bin/cxx-asan/osh run-test-funcs

  echo TODO: enable
}

run-for-release() {
  run-other-suite-for-release json-errors run-test-funcs
}

"$@"
