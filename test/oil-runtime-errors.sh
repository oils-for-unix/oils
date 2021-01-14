#!/usr/bin/env bash
#
# Usage:
#   ./oil-runtime-errors.sh <function name>

# NOTE: No set -o errexit, etc.

source test/common.sh

OIL=${OIL:-bin/oil}

banner() {
  echo
  echo ===== CASE: "$@" =====
  echo
}

_error-case() {
  banner "$@"
  echo
  $OIL -c "$@"

  # NOTE: This works with osh, not others.
  local status=$?
  if test $status != 1; then
    die "Expected status 1, got $status"
  fi
}

_should-run() {
  banner "$@"
  echo
  $OIL -c "$@"

  local status=$?
  if test $status != 0; then
    die "Expected it to parse"
  fi
}


regex_literals() {
  _should-run "var sq = / 'foo'+ /"

  _error-case '
  var dq = / "foo"+ /
  echo $dq
  '

  _should-run '
  var dq = / ("foo")+ /
  echo $dq

  var dq2 = / <"foo">+ /
  echo $dq2
  '

  _error-case '
  var literal = "foo"
  var svs = / $literal+ /
  echo $svs
  '

  _error-case '
  var literal = "foo"
  var bvs = / ${literal}+ /
  echo $bvs
  '
}

undefined_vars() {
  set +o errexit

  _error-case 'echo hi; y = 2 + x + 3'
  _error-case 'if (x) { echo hello }'
  _error-case 'if ($x) { echo hi }'
  _error-case 'if (${x}) { echo hi }'

  # BareDecl and regex
  _error-case 'x = / @undef /; echo hi'

  _error-case 'var x = undef; echo $x'  # VarDecl
  _error-case 'setvar a = undef'  # PlaceMutation
}

_run-test() {
  local name=$1

  bin/osh -O oil:basic -- $0 $name
}

run-all-with-osh() {
  _run-test regex_literals
  _run-test undefined_vars

  return 0  # success
}

run-for-release() {
  run-other-suite-for-release oil-runtime-errors run-all-with-osh
}

"$@"
