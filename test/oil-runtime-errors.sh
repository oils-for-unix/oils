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

_error-case-X() {
  local expected_status=$1
  shift

  banner "$@"
  echo
  $OIL -c "$@"

  # NOTE: This works with osh, not others.
  local status=$?
  if test $status != $expected_status; then
    die "Expected status $expected_status, got $status"
  fi
}

_error-case() {
  ### Expect status 1
  _error-case-X 1 "$@"
}

_expr-error-case() {
  ### Expect status 3
  _error-case-X 3 "$@"
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

test-regex-literals() {
  set +o errexit

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

test-undefined-vars() {
  set +o errexit

  _error-case 'echo hi; const y = 2 + x + 3'
  _error-case 'if (x) { echo hello }'
  _error-case 'if ($x) { echo hi }'
  _error-case 'if (${x}) { echo hi }'

  # BareDecl and regex
  _error-case 'x = / @undef /; echo hi'

  _error-case 'var x = undef; echo $x'  # VarDecl
  _error-case 'setvar a = undef'  # PlaceMutation
}

test-oil-word-eval() {
  set +o errexit

  _error-case 'echo $maybe("foo")'

  _error-case 'echo $identity({key: "val"})'

  # this should be consistent
  _error-case 'write -- @identity([{key: "val"}])'

  _error-case 'const x = [1, 2]; echo $x'
}

test-oil-expr-eval() {
  set +o errexit

  _expr-error-case 'echo $[42 / 0 ]'

  _expr-error-case 'var d = {}; var item = d->nonexistent'

  _expr-error-case 'var d = {}; var item = d["nonexistent"]'

  _expr-error-case 'var a = []; setvar item = a[1]'

  _expr-error-case 'const x = 42 / 0'

  # command sub as part of expression retains its exit code
  _error-case 'var x = "z" ++ $(false)'
  #_error-case 'var x = "z" ++ $(exit 42)'

  _expr-error-case 'case $[42 / 0] { (*) echo hi ;; }; echo OK'

  _expr-error-case 'var d = {}; for x in $[d->zzz] { echo hi }'
}

soil-run() {
  run-test-funcs
}

run-for-release() {
  run-other-suite-for-release oil-runtime-errors run-test-funcs
}

"$@"
