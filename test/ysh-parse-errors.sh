#!/usr/bin/env bash
#
# Usage:
#   test/ysh-parse-errors.sh <function name>

source test/common.sh

YSH=${YSH:-bin/ysh}

banner() {
  echo
  echo ===== CASE: "$@" =====
  echo
}

_error-case() {
  banner "$@"
  echo
  $YSH -n -c "$@"

  local status=$?
  if test $status != 2; then
    die "Expected a parse error, got status $status"
  fi
}

_should-parse() {
  banner "$@"
  echo
  $YSH -n -c "$@"

  local status=$?
  if test $status != 0; then
    die "Expected it to parse"
  fi
}

test-return-args() {
  set +o errexit

  _should-parse '
  func foo(x) {
    return (x)
  }
  '

  _error-case '
  func foo(x) {
    return ()
  }
  '

  _error-case '
  func foo(x) {
    return (named=x)
  }
  '

  _error-case '
  func foo(x) {
    return (x, named=x)
  }
  '

  _error-case '
  func foo(x) {
    return (x, x)
  }
  '
}

soil-run() {
  # This is like run-test-funcs, except errexit is off here
  run-test-funcs
}

run-for-release() {
  run-other-suite-for-release ysh-parse-errors run-test-funcs
}

"$@"

